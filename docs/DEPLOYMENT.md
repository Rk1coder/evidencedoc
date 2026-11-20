# Deployment

## Local or Docker inference

The root Dockerfile builds the checked-out application. The server uses port 7860 and binds to loopback locally unless `HOST` is set. Both modes perform real model inference; the first answer downloads and loads the pinned model.

## Public Hugging Face preview

The public Space uses the free Static SDK. `site/index.html` is a self-contained interactive preview of real recorded CPU results, source-page images, sample downloads, and JSON reports. It does not accept document uploads or expose a Gradio inference API.

The preview embeds the measured reports and checksum-verified sample. Its labels explicitly distinguish recorded results from live inference. The source code, development data, and full local application are linked from the page.

## Hosting the Python application

At publication, the account's Space creation form restricted new Gradio and Docker Spaces to a paid plan. No subscription or paid hardware was enabled. A compute-enabled account can deploy the root application as a Gradio or Docker Space; eligible personal accounts may have a separate free ZeroGPU allowance, which requires a compatible GPU deployment and account eligibility checks.

See the current [Hugging Face Spaces documentation](https://huggingface.co/docs/hub/spaces-overview) and [ZeroGPU requirements](https://huggingface.co/docs/hub/spaces-zerogpu). Do not treat the Static preview URL as a model inference endpoint. No deployment credentials are stored in this repository.

Regenerate the recorded-results page with `python scripts/build_preview.py` after restoring the sample and intentionally updating the measured result files. No inference is run by the preview builder.
