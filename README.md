# adding a new method with cfs from a csv file

This scripts help to quickly parse a csv file and:

+ create new nodes
+ generate a new LCIA method based on the data from the file.

## Use

### To create a completely new method

You can use the script as described below to _create a new method_ with only the CFs from the file.

```python
import bw2data as bd

# Set the project
bd.projects.set_current('ecoinvent-3.12-cutoff')
# import the functions from the file

##
from add_new_cfs import parse_new_flows_from_csv, parse_node_ids_and_cfs

### First, create the new nodes
### and add them to a new database
new_flows = parse_new_flows_from_csv('tests/fixtures/sample_medical_substances.csv')
# The new database name is meant to be the same that you put inthe csv file "new_database" column
new_db = bd.Database('additional_chemical_flows')
new_db.register()
new_db.write(new_flows)

### Second, create the method and add the new charaterisation flows
new_cfs = parse_node_ids_and_cfs('tests/fixtures/sample_medical_substances.csv')
new_method = bd.Method(('additional method', 'usetox_extensions', 'cat1', 'cat2'))
new_method.register()
new_method.write(new_cfs)

### Verification that it work can be done with:
new_method = bd.Method(('additional method', 'usetox_extensions', 'cat1', 'cat2'))
new_method.load()
bd.get_node(id=247406338651054080)
```

### To add the new cfs to an existing method (and create a new one)

You can use the script as described below to take the CFs from another method, add the new CFs from the csv file and create a totally new method.

```python
import bw2data as bd

# Set the project
bd.projects.set_current('ecoinvent-3.12-cutoff')
# import the functions from the file

##
from add_new_cfs import parse_new_flows_from_csv, parse_node_ids_and_cfs

### First, create the new nodes
### and add them to a new database
new_flows = parse_new_flows_from_csv('tests/fixtures/sample_medical_substances.csv')
# The new database name is meant to be the same that you put inthe csv file "new_database" column
new_db = bd.Database('additional_chemical_flows')
new_db.register()
new_db.write(new_flows)

### Second, parse the new cfs
new_cfs = parse_node_ids_and_cfs('tests/fixtures/sample_medical_substances.csv')

### Third, load the cfs of another method
other_method = bd.Method(('USEtox v2.13','endpoint','ecosystem quality','ecotoxicity: freshwater'))
other_method_cfs = other_method.load()

new_method = bd.Method(('additional method', 'usetox_extensions', 'cat1', 'cat2'))
new_method.register()
all_cfs = other_method_cfs.extend(new_cfs)
new_method.write(new_cfs)

### Verification that it work can be done with:
new_method = bd.Method(('additional method', 'usetox_extensions', 'cat1', 'cat2'))
new_method.load()
bd.get_node(id=247406338651054080)
```


