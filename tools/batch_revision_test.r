# \file
# \brief job
# \author Ton Smeele, Sietse Snel
# \copyright Copyright (c) 2015-2021, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE


kickOffRevisionBatch {
    *verbose='1'; # ('1': yes, not '1': no)
    # Kick off batch processing -> data_id=0
    *data_id = '0';
    *max_batch_size = '1';
    *delay = '1';
    uuRevisionBatchRule(*verbose, *data_id, *max_batch_size, *delay);
}

input *intakeRoot='dummy'
output ruleExecOut
