# Deployment

## Local or Docker

The root Dockerfile builds the source checked out in the current directory. The application uses port 7860 and binds to loopback locally unless `HOST` is set.

## Hugging Face Space

The public Docker Space is configured with a fixed GitHub source commit. Its Dockerfile downloads that commit's source archive, installs its pinned runtime dependencies, and starts `app.py` as an unprivileged user.

This release contract keeps the demo linked to a reviewable source revision. A new GitHub commit does not silently change the running demo. After tests pass, update the Space's `SOURCE_REVISION` to deploy another revision. Model files are downloaded separately from the pinned model revision in `evidencedoc/inference.py`.

No deployment credential is included in this repository. Public hosting has separate resource limits from the locally tested machine; a successful build alone does not establish successful model inference. Verify an actual document upload, citation preview, and matching JSON download after deployment.
