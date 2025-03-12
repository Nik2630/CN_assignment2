# Define script paths
scripts=(
    "nagle.py"
    "server.py"
    "client.py"
    "run_experiment.py"
)

# Make all scripts executable
for script in "${scripts[@]}"; do
    chmod +x "$script"
done

# make results directory
results_dir="results"
mkdir -p "$results_dir"

echo "Starting experiment using the nagle.py script..."
sudo python3 nagle.py 

# Make results accessible to the user
sudo chown -R $USER:$USER "$results_dir"
