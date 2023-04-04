# Sometimes data requests are manually edited in place (e.g. for small textual
# changes). This in-place editing is done on the datarequest.json file.

# The contents of this file are set as AVUs on the file itself. This is only
# done once, at the submission of the datarequest. Therefore, to keep the AVUs
# of datarequest.json files accurate after a manual edit of the data request, we
# need to resynchronize the AVUs with the updated contents of the
# datarequest.json.

# This script does exactly that. It takes exactly 1 numeric argument (the
# request ID of the data request).

def main(rule_args, callback, rei):
  empty = ""
  request_id = global_vars['*request_id']
  if request_id == None or not request_id.isdigit():
    callback.writeLine('stdout', 'No (valid) request_id specified (must be an integer). Exiting.')
  else:
    ret = callback.rule_datarequest_sync_avus(request_id, empty)
    callback.writeLine('stdout', 'AVUs synced for datarequest {}.'.format(request_id))

input *request_id=None
output ruleExecOut
