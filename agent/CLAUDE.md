The user will provide you with instructions for edits to the part of this repository that together proviede a collection repository, on Github, collecting some interesting resources related to Claude Code.

## Repo map

/data (relative to the repo base) contains data files in which repositories and categories are stored. Some categories are hierarchial/have subcategories. Each category has a short description. 

## Workflow

The user may ask you to:

- Add repos with existing categories
- Remove repos
- Edit repos
- Reorganise/recategorise repos
- Scan the index for redundancy/opportunities to consollidate

## Readme Generation

The data file is periodically constructed into the readme. This is done using the scripts in /scripts

When the user asks you to regenerate the readme, run this script.

## Task Management

The user will use a tasks folder (/tasks relative to this level of the repo) in which to gather lists of edits to the repo. Tasks will be gathered in /to-add as markdown docs. When you have completed the task, you can move the doc into the /added subfolder.

## Deployment

When the user asks you to push the repo to github, recurse to the base of the repsitory then git add ., git commit -m "{message}", git push

The commit message can be a summary of these updates.