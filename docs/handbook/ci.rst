CI Integration
==============

It is also possible to integrate CEKit into your continuous integration via a GitHub Action. The action is available  `here <https://github.com/manusa/actions-setup-cekit>`_.

An example of its usage (from `jkube-images <https://github.com/jkubeio/jkube-images/blob/main/.github/workflows/build-images.yml>`_ is:

.. code-block:: yaml

    name: Build Images

    on:
      pull_request:
      push:
        branches:
          - main

    env:
      TAG: latest

    jobs:
      build-images:
        name: Build Images
        runs-on: ubuntu-latest
        strategy:
          fail-fast: false
          matrix:
            image: ['jkube-java-binary-s2i', 'jkube-jetty9-binary-s2i', 'jkube-karaf-binary-s2i', 'jkube-tomcat9-binary-s2i']
        steps:
          - name: Checkout
            uses: actions/checkout@v2
          - name: Install CEKit
            uses: manusa/actions-setup-cekit@v1.1.1
          - name: Build java-binary-s2i
            run: |
              echo "Building quay.io/jkube/${{ matrix.image }}:${TAG}"
              cekit --descriptor ${{ matrix.image }}.yaml build docker --tag="quay.io/jkube/${{ matrix.image }}:${TAG}"
