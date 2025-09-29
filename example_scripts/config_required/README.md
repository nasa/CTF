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

As an example of named sections, see `configs/example_lx1_lx2_config.ini`. It contains multiple named sections:

* `[cfs_LX1]`
* `[cfs_LX2]`
* `[ssh]`

If provided with a test that does not register targets, the CFS plugin would then configure targets for each of `cfs_LX1`,
`cfs_LX2`. Alternatively, a test may explicitly register any combination of the above targets.

### Test scripts

The test scripts in this directory each explicitly register a single target from the above config file that uses a different 
protocol. Other example tests typically do not register targets, and so will configure whatever is found in the config file.

* `CFS_LX1_Registered_Config_Test.json` registers `cfs_LX1` as the target, which uses the `local` protocol

Each of these tests should be run with the config file `configs/example_lx1_lx2_config.ini` or another config file that 
defines a section for the corresponding target name.
