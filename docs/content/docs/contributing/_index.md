---
title: Contributing
weight: 6
cascade:
  type: docs
---

Contributions are welcome! Whether you're adding a new component, improving the documentation, or fixing a bug, please follow this general workflow.

## Contribution Workflow

1.  **Fork:** Create your personal fork of the `dev7a/ocelot` repository on GitHub.
2.  **Clone:** Clone your fork to your local development machine.
    ```bash
    git clone https://github.com/YOUR-USERNAME/ocelot.git
    cd ocelot
    ```
3.  **Branch:** Create a new feature branch for your changes. Choose a descriptive name.
    ```bash
    git checkout -b feature/my-cool-addition
    ```
4.  **Develop:**
    -   Implement your new component, distribution changes, or other improvements.
    -   Follow the process in [Adding New Components]({{< relref "/docs/components/adding-components" >}}) if you're adding a component.
    -   Ensure any necessary documentation is added or updated.
5.  **Test Locally:** Use the local build script to verify that your changes build successfully and function as expected.
    ```bash
    uv run tools/ocelot.py --distribution YOUR_DISTRIBUTION
    ```
6.  **Commit & Push:** Commit your changes with clear, descriptive messages and push the branch to your fork.
    ```bash
    git add .
    git commit -m "feat: Add my cool addition"
    git push origin feature/my-cool-addition
    ```
7.  **Pull Request:** Open a Pull Request from your feature branch to the `main` branch of the original `dev7a/ocelot` repository. Provide a detailed description of your contribution in the PR description.
8.  **Review:** Engage in the review process and address any feedback from the maintainers.

## Setting Up a Fork for Publishing

If you want to use GitHub Actions in your own fork to publish layers to your personal AWS account, see the [Setup Fork for Automated Publishing](setup-fork) guide. 