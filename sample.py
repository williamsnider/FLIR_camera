# Generate sampling data
import numpy as np

CONSEC_LIMIT = 3


def score_seq(seq):

    # Convert to sequence of trial types
    seq_trial_types = []

    for i in range(1, len(seq)):

        stimA = seq[i - 1]
        stimB = seq[i]

        if stimA == stimB:
            seq_trial_types.append("S")
        else:
            seq_trial_types.append("L")

    num_S = seq_trial_types.count("S")
    num_L = seq_trial_types.count("L")
    max_S_consec = max([len(s) for s in "".join(seq_trial_types).split("L")])
    max_L_consec = max([len(s) for s in "".join(seq_trial_types).split("S")])

    # print("num_S:    ", num_S)
    # print("num_L:    ", num_L)
    # print("consec_S: ", max_S_consec)
    # print("consec_L: ", max_L_consec)

    return num_S, num_L, max_S_consec, max_L_consec


trial_types = ["L", "S"]
stimuli_list = ["A", "B", "C", "D", "E"]
NUM_REPETITIONS = 5


num_stimuli = len(stimuli_list)
num_trials = num_stimuli * NUM_REPETITIONS

# Generate list to shuffle from
stimuli_list_with_reps = stimuli_list * NUM_REPETITIONS
np.random.shuffle(stimuli_list_with_reps)

# Generate sequence of stimuli

seq_stimuli_best = []
seq_length_best = 1e6

while True:
    seq_stimuli = []
    seq_length = 0
    stim_counts = {stim: 0 for stim in stimuli_list}
    while True:

        if seq_length == 0:
            stim = np.random.choice(stimuli_list)
        else:

            trial_type = np.random.choice(trial_types)
            if trial_type == "S":
                stim = seq_stimuli[-1]
            else:
                stim_list_without_prev = stimuli_list.copy()
                stim_list_without_prev.remove(seq_stimuli[-1])
                stim = np.random.choice(stim_list_without_prev)

        seq_stimuli.append(stim)
        seq_length += 1
        stim_counts[stim] += 1

        # Test if all counts >= NUM REPETITIONS
        if all([count >= NUM_REPETITIONS for count in stim_counts.values()]):
            break

    num_S, num_L, max_S_consec, max_L_consec = score_seq(seq_stimuli)

    if (seq_length <= seq_length_best) and (max_S_consec <= CONSEC_LIMIT) and (max_L_consec <= CONSEC_LIMIT):
        seq_length_best = seq_length
        seq_stimuli_best = seq_stimuli

        print("*" * 20)
        print(seq_stimuli_best)
        print(seq_length_best)
        score_seq(seq_stimuli_best)


# # Generate sequence of L and S trials
# seq_types = trial_types * ((num_trials + 1) // 2)
# np.random.shuffle(seq_types)


# # Sample from stimuli_list without replacement
# stimuli_with_reps = {stim: NUM_REPETITIONS for stim in stimuli_list}
# seq_stimuli = []

# for i in range(num_trials):

#     # Select random initial stimulus
#     if i == 0:
#         stim = np.random.choice(list(stimuli_with_reps.keys()))

#     else:
#         # Select subsequent stimulus based on L and S
#         trial_type_current = seq_types[i]
#         prev_stim = seq_stimuli[i - 1]
#         if trial_type_current == "S":
#             stim = seq_stimuli[-1]
#         else:
#             # Choose stimulus with largest count remaining
#             stimuli_with_repts_without_prev = stimuli_with_reps.copy()
#             stimuli_with_repts_without_prev.pop(prev_stim)
#             stim = min(stimuli_with_repts_without_prev, key=stimuli_with_reps.get)

#     print("*****")
#     print(stimuli_with_reps)
#     print(seq_stimuli)
#     seq_stimuli.append(stim)
#     stimuli_with_reps[stim] -= 1

#     if stimuli_with_reps[stim] == 0:
#         stimuli_with_reps.pop(stim)
