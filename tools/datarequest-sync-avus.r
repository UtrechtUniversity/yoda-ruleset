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
