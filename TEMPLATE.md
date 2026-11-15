# Project Organization Template

## For agents: how to use this document

Every work item in a project is classified on three fields:

- **Stage**: where the item is in its life, from idea to observed behaviour.
- **Type**: what kind of work it is.
- **Domain**: which part(s) of the project it touches.

Rules:

1. **Every item has exactly one current stage, one type, and one or more domains.** Set the type and domain(s) when the item is created.
2. **Items need not pass through every stage.** Record the stage an item *entered* at as well as its *current* stage. Most bugs, refactors and chores skip stages -2 to 0.
3. **Negative stages are exploratory and disposable; stage 0 is the gate; positive stages are committed work.** Do not treat spike code (-1) as production code.
4. **Use only the types and domains defined here.** If nothing fits, flag it for the project owner rather than inventing a new value.
5. **Read only what your task needs.** Query items by stage, type or domain instead of reading every record.

---

### Stages
All projects have all of these stages.

| Stage | Step            | Description                                                                                                                  |
| :---: | --------------- | ---------------------------------------------------------------------------------------------------------------------------- |
|  -2   | Idea            | An idea for a feature performance improvement, etc.                                                                          |
|  -1   | Spike           | A potentially throwaway piece of code that assesses technical feasibility and performance.                                   |
|   0   | Decision        | Commit, reject, or park. Every outcome gets a short verdict record with a reason and, for park, a revisit trigger.           |
|   1   | Intent          | What this work item should achieve and why, in one or two plain sentences. Committed work, no detail on *how* yet.           |
|   2   | specification   | A written specification of the intent.                                                                                       |
|   3   | unit test (TDD) | Test to ascertain whether the implementation of the spec is successful.                                                      |
|   4   | implementation  | The development of the specifications.                                                                                       |
|   5   | test suite      | Testing the whole assembly, the whole application to ensure that the new work doesn't impact other elements of the assembly. |
|   6   | Observed        | Real-world behaviour and benchmarks, with an environment snapshot.                                                           |

### Types
All projects have all of these types. For larger and more complex projects, these types may be expanded.

Every item has exactly one type. The type tells you what the work is and where it usually enters the stages.

| Type        | Definition                                                              | Usually enters at          | Notes                                                                    |
| ----------- | ----------------------------------------------------------------------- | :------------------------: | ------------------------------------------------------------------------ |
| Feature     | A new capability.                                                       | -2                         |                                                                          |
| Bug         | Implementation does not match the specification.                        | 1                          |                                                                          |
| Enhancement | Improves an existing capability (speed, UX, memory).                    | -2 (-1 for perf work)      | Performance work links to its benchmark results.                         |
| Refactor    | Changes structure without changing behaviour.                           | 2                          | Existing tests are the spec and must not change. If they do, it is not a refactor. |
| Chore       | Maintenance with no user-facing change (dependency bumps, cleanup).     | 2                          |                                                                          |

### Domains
Every project must have one or more domains, though the domains that they have are determined by the project. For example, a project could be about documentation only. A Python basic script might have 'core', 'testing' and 'documentation' domains only.

An item can touch several domains. For example, a new CLI argument may be CLI + documentation + testing. Use only the domains the project has declared in `z.toml`.

| Domain | Key (in `z.toml`) | Covers |
| --- | --- | --- |
| Dev environment | `dev-env` | Local tooling, setup and developer workflow. |
| Documentation | `documentation` | User and developer docs. |
| Testing | `testing` | Test code and test harnesses. |
| CI | `ci` | Automated build and test pipelines. |
| Core | `core` | The engine / main library. |
| Models/data | `models-data` | Models, datasets and data handling. |
| Packaging/release | `packaging-release` | Builds, distribution and versioning. |
| Back-end | `back-end` | Server-side code. |
| Front-end | `front-end` | User interface. |
| CLI | `cli` | Command-line interface. |
| API | `api` | Programmatic interfaces exposed to other code. |
