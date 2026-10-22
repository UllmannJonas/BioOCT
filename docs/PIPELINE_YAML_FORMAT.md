# Pipeline YAML format history

Developer reference only. YAML structure versions are independent of the BioOCT
package version.

| YAML version | BioOCT version | Git reference | Structure |
| --- | --- | --- | --- |
| 0.0 | 0.4.2 | Release tag [`v0.4.2`](https://github.com/UllmannJonas/BioOCT/tree/v0.4.2), `b70411283cc2de2bc4e3efc7001d1fa13b43f12a` | Root contains `created with` and `pipeline`. File-producing steps store a path template in `params.path`, commonly using `$source_dir` and `$layer_name`. |
| 0.1 | 0.4.2 | Current change based on `c0fe297b37dfc2981a7297054c4684b3c464fe75` (not yet committed) | Root contains `pipeline`; file-producing steps use `params.output_filename`. `{input_layer}` resolves from the first input layer. Replay supplies the resolved filename as the function's `path`. |

The `created with` field is informational and ignored when loading old files.
Legacy string `path` templates remain supported; `$layer_name` retains its
original base-layer meaning. The output-folder override is a replay-session
choice and is not stored in YAML.

Versioning: increment the minor YAML version for developer-visible structure
changes that are invisible to users. Increment the major version for changes
visible to users.
