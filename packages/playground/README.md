# Playground Core

This package contains the shared Playground core library:

- persona loading
- user simulation
- in-process Harbor host-native runners (`playground.inprocess`)
- scoring helpers

This package is the shared Playground core library used by the app backend and
runtime adapters.

Some modules still rely on the in-repo Playground backend source tree (`backend.*`).
