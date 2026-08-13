# Architecture diagram sources

The two SVGs in this directory are editable source artifacts (text, shapes, and
embedded icon data) and are intentionally kept in the repository so the
architecture remains reviewable without a diagram SaaS account. Each exported
diagram is standalone: it does not depend on a neighboring file or hosted
asset when rendered by GitHub.

The cloud diagram uses unchanged service icons from the official Microsoft Azure
Architecture Icons collection, V24:

<https://learn.microsoft.com/en-us/azure/architecture/icons/>

The downloaded collection is distributed under Microsoft's icon terms. The
original icon SVGs remain in `assets/` for provenance, while the cloud export
embeds byte-equivalent base64 data URIs. The icons are not cropped, flipped,
rotated, recolored, or distorted. The cloud
diagram is a Terraform design review artifact; the label “CLOUD DEPLOYMENT NOT
EXECUTED” is intentional because no Azure apply occurred in this repository.
