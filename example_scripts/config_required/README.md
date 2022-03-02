# Config required tests

The tests in this directory demonstrate the use of config sections to provide parameters for CFS targets. For more information
on CFS configuration, see [CFS Plugin.](../../plugins/cfs/README.md)

## Using config sections

There are two ways to use config sections: with or without registration. With registration using the `RegisterCfs` instruction,
only those targets registered will be configured. Without registration, the plugin will automatically configure targets for 
each config section name beginning with `cfs_`. In either case, values found in a named config section will override any defaults
found in the `[cfs]` section. If no such sections are found, the target will be a single local instance using the
`[cfs]` section defaults. In any case, subsequent instructions that do not specify a name will be executed against any and
all configured targets per the above rules.

## Examples

### Config file

As an example of named sections, see `configs/cfe_6_7_config_examples.ini`. It contains multiple named sections:

* `[cfs_LX1]`
* `[cfs_LX2]`
* `[cfs_SP01]`
* `[cfs_SP02]`
* `[local_ssh]`

If provided with a test that does not register targets, the CFS plugin would then configure targets for each of `cfs_LX1`,
`cfs_LX2`, `cfs_SPO1`, and `cfs_SP02` (but not `local_ssh` because it does not match the naming convention).
Alternatively, a test may explicitly register any combination of the five targets to use only those.

### Test scripts

The test scripts in this directory each explicitly register a single target from the above config file that uses a different 
protocol. Other example tests typically do not register targets, and so will configure whatever is found in the config file.

* `cfs_LX1_registered_config.json` registers `cfs_LX1` as the target, which uses the `local` protocol
* `cfs_SP01_registered_config.json` registers `cfs_SPO1` as the target, which uses the `sp0` protocol
* `local_ssh_registered_config.json` registers `local_ssh` as the target, which uses the `ssh` protocol

Each of these tests should be run with the config file `configs/cfe_6_7_config_examples.ini` or another config file that 
defines a section for the corresponding target name.