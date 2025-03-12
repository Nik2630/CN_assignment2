# Ensure the script is executed with root privileges
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root" 1>&2
    echo "Try: sudo ./run_all_simple.sh" 1>&2
    exit 1
fi

# Create a directory for results
mkdir -p results

# make scripts executable
chmod +x run_experiments.py analyze_results.py

# Execute all experiments and analyze results
for option in a b c d; do
     echo "Executing experiment $option"
     sudo python3 run_experiments.py --option=$option
    #  echo "Analyzing results for experiment $option"
    #  python3 analyze_results.py --experiment=$option
done

# Perform a analysis of all results
echo "===== Performing analysis of results ====="
python3 analyze_results.py --experiment=all

echo "===== All experiments have been executed ====="
echo "Results can be found in the 'results' directory"
