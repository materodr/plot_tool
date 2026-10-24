Process of collaboration
1. The project must me kept on gitlab repo.
2. The gitlab repo must be structure using the following branch types: 1 - a permanent main branch, 2- a permanent develop branch, 3 - feature branches created as needed, 4 - fix branches created as needs.
3. Tha name of each branch must clearly refer to one of the allowed type of branches
4. An gitlab issue must be created to map the development for every fix and new feature.
5. The feature and fix branches must always be created pointing to an issue. Must be explicit on the title of the branch.
6. A fix issue must contain a description of the bug, how severe is the bug, a step by step description of how the bug can be reproduced, what is the solution, how the solution was tested, and the evidence showing the solution actually solves the bug.
7. The serverity of the bug must be classified in: low, medium and high.
8. The feature issue must contain a description of the feature, why the app needs it, what is the urgency of the implementation, how the implementation was done, what tests were used to check if the implementation holds true do the feature and what is the evidence that it holds true.
9. The urgency of the feature in the issue must be classified in: low, medium and high.
10. The priority of work must be given to issues of features with higher urgency or bugs with higher severity.
11. Between a feature of high urgency and a fix of high serverity, the fix of high severity must have priority.
12. A feature or fix must only start to be tackled when the issue to track it is already created.
13. If in the process of creating a feature or fixing a bug, a new bug is found: a)if the bug is correlated with the in going work, fix the bug using the same issue, b) if it is not correlated an issue needs to be open.
14. A merge request can only happen if the issue have all the information described in req x.
15. Main branch merge requests must be approved by humans.
16. Other branch merge can be done by ai agents after an agent different from the one that did the implementation review and test independently.
17. A merge request from develop to main must list all the issues that track all the code change since the last merge.
18. The merge request from develop to branch must show evidence that the code fulfils all the functional requirements.
19. A table named test matrix must be permanently keep on tests folder.
20. The first column of the test matrix must contain the current set of high level functional requirements.
21. The second column must show for each hlfr what are the children llfr.
22. The third column must contain the tests linked to each hlfr and show their last run status as passed or failed.
23. The fourth must contain the pass if all tests passed and fail if at least one test failed.
24. The agents must write tests that cover with robustness every aspect of the high level requirements.
25. The development and main branch must be kept free of crashes.
26. Worktress must be used to keep each agent a separate environment
