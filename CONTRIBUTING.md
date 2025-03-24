# Contributing to Transcript Podcastify

Thank you for your interest in contributing to Transcript Podcastify! This document provides guidelines and steps for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. We expect all contributors to:
- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/transcription_podcastify.git
   cd transcription_podcastify
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/rileylemm/transcription_podcastify.git
   ```
4. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

1. Set up your development environment following the README.md instructions
2. Make your changes in your feature branch
3. Keep your branch updated with upstream:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
4. Run tests and ensure they pass
5. Update documentation as needed
6. Push your changes to your fork
7. Submit a pull request

## Pull Request Process

1. Create a pull request from your feature branch to the main repository's `main` branch
2. Use our pull request template
3. Ensure the PR description clearly describes the problem and solution
4. Include the relevant issue number if applicable
5. Update the README.md with details of changes if applicable
6. The PR must receive approval from at least one maintainer
7. All automated checks must pass

### Pull Request Template

```markdown
## Description
[Describe the changes you've made]

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
[Describe the tests you ran]

## Checklist:
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

## Commit Message Guidelines

We follow the Conventional Commits specification. Each commit message should be structured as follows:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools

Example:
```
feat(transcription): add support for multiple language transcripts

- Added language detection
- Implemented translation service integration
- Updated UI to show language options

Closes #123
```

## Branch Naming Convention

Use the following format for branch names:
- Feature branches: `feature/description-in-kebab-case`
- Bug fixes: `fix/description-in-kebab-case`
- Documentation: `docs/description-in-kebab-case`
- Performance improvements: `perf/description-in-kebab-case`

Example: `feature/multi-language-support`

## Development Environment

1. Required Dependencies:
   - Python 3.9+
   - Docker and Docker Compose
   - Node.js 16+ (for frontend development)

2. Environment Setup:
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Set up pre-commit hooks
   pre-commit install
   ```

3. Docker Development:
   ```bash
   # Start services
   docker-compose -f docker-compose.dev.yml up --build
   ```

## Testing Guidelines

1. Write tests for new features and bug fixes
2. Maintain or improve code coverage
3. Run the test suite before submitting:
   ```bash
   pytest
   ```
4. Include both unit and integration tests when applicable

## Documentation

1. Update documentation for any new features or changes
2. Document functions and classes using docstrings
3. Keep the README.md up to date
4. Add comments for complex logic
5. Update API documentation if applicable

## Questions or Need Help?

Feel free to:
- Open an issue for questions
- Join our discussions
- Reach out to maintainers

Thank you for contributing to Transcript Podcastify! 