from persona.human_extraction.scripts import run_extraction_amazon as amazon


def _review(review_id: str, timestamp: int, **overrides):
    row = {
        "review_id": review_id,
        "category": "Kitchen",
        "parent_asin": f"PARENT-{review_id}",
        "asin": f"ASIN-{review_id}",
        "timestamp": timestamp,
        "rating": 5,
        "title": "Useful",
        "text": "Detailed review text with enough evidence.",
        "verified_purchase": True,
        "helpful_vote": 1,
    }
    row.update(overrides)
    return row


def test_filter_reviews_and_temporal_split_keep_supported_rows():
    reviews = [
        _review("1", 1000, title="", text="", product_title="Cast iron pan"),
        _review("2", 2000, title="great product", text=""),
        _review("3", 3000, rating=9),
        _review("4", 4000, text="Specific cooking details and build quality notes."),
        _review(
            "4-dup",
            4000,
            parent_asin="PARENT-4",
            asin="ASIN-4",
            text="Specific cooking details and build quality notes.",
        ),
    ]

    kept, summary = amazon.filter_reviews(
        reviews,
        min_review_text_chars=20,
        filter_fulfillment_reviews=True,
    )
    construction, validation, split = amazon.temporal_train_validation_split(
        kept,
        train_fraction=0.5,
    )

    assert [row["parent_asin"] for row in kept] == ["PARENT-1", "PARENT-4"]
    assert summary["removed_by_reason"]["missing_or_invalid_rating"] == 1
    assert any(reason.startswith("fulfillment_or_template") for reason in summary["removed_by_reason"])
    assert len(construction) == 1
    assert len(validation) == 1
    assert split["construction_row_count"] == 1
    assert split["validation_row_count"] == 1


def test_summary_stats_and_profile_render_rating_only_product_context():
    row = {
        "user_id": "USER",
        "temporal_split": {
            "construction_row_count": 2,
            "validation_row_count": 1,
            "construction_text_review_count": 1,
            "construction_rating_count": 2,
        },
        "reviews": [
            _review(
                "1",
                1000,
                title="",
                text="",
                product_title="Cast Iron Pan",
                product_main_category="Amazon Home",
                product_category_path=["Kitchen", "Cookware"],
            ),
            _review("2", 2000, text="I cook at home most weekends."),
        ],
    }
    row["category_review_stats"] = amazon.category_review_stats(row["reviews"])

    profile = amazon.assemble_profile(row, max_chars=5000, max_review_text_chars=200)

    assert "=== Summary Stats ===" in profile
    assert "rating_only=1" in profile
    assert "rating_only_products=Cast Iron Pan=1" in profile
    assert "product_title: Cast Iron Pan" in profile
    assert "product_category_path: Kitchen > Cookware" in profile


def test_attach_product_metadata_updates_reviews_and_recomputes_stats(monkeypatch):
    rows = [
        {
            "reviews": [
                {
                    "category": "Kitchen",
                    "parent_asin": "PARENT1",
                    "timestamp": 1000,
                    "rating": 5,
                    "title": "",
                    "text": "",
                }
            ],
            "validation_reviews": [],
        }
    ]
    bucket = amazon.parent_asin_bucket("PARENT1")
    filename = (
        "amazon/modal_artifacts/amazon_reviews_2023_metadata_by_parent_asin_bucket_v2/"
        f"bucket={bucket}/source_category=Kitchen/part-000000.parquet"
    )

    monkeypatch.setattr("huggingface_hub.hf_hub_download", lambda **_kwargs: "/tmp/fake.parquet")

    class FakeFrame:
        def to_dict(self, orient):
            assert orient == "records"
            return [
                {
                    "parent_asin": "PARENT1",
                    "source_category": "Kitchen",
                    "main_category": "Amazon Home",
                    "title": "Carbon Steel Pan",
                    "categories_json": '["Kitchen", "Cookware"]',
                }
            ]

    monkeypatch.setattr(amazon.pd, "read_parquet", lambda *_args, **_kwargs: FakeFrame())

    summary = amazon.attach_product_metadata(
        rows,
        repo_files=[filename],
        repo_id="MatrAIx2026/MatrAIx2026",
        metadata_prefix=amazon.METADATA_PREFIX,
        token=None,
        download_delay_seconds=0.0,
    )

    review = rows[0]["reviews"][0]
    assert summary["matched_review_rows"] == 1
    assert review["product_title"] == "Carbon Steel Pan"
    assert rows[0]["category_review_stats"]["Kitchen"]["rating_only_product_title_counts"] == {
        "Carbon Steel Pan": 1
    }
