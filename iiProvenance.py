
# \brief Frontend function to add action log record to specific folder
#
# \param[in] actor     rodsaccount coming from yoda frontend
# \param[in] folder    folder the logging is linked to
# \param[in] action    the text that is logged

def iiFrontEndAddActionLogRecord(rule_args, callback, rei):
        actor, folder, action = rule_args[0:3]

	# actor to be reformatted to yoda user - name#zone
        this_actor = actor.split(':')[0].replace('.','#')

        status = 'Success'
        statusInfo = ''

        def report(x):
            #callback.writeString("serverLog", x)
            callback.writeString("stdout", x)

        callback.iiAddActionLogRecord(this_actor, folder, action)

        report(json.dumps({'status':     status,
                           'statusInfo': statusInfo}))
        return




