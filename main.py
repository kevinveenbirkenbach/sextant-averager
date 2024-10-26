import argparse
import re
from datetime import datetime
from statistics import mean, stdev
from tabulate import tabulate

# Function to check format HH:MM:SS@00°00.0' and convert to decimal degrees
def parse_measurement(value):
    try:
        time_part, degree_part = value.split('@')
        datetime.strptime(time_part, '%H:%M:%S')
        
        # Extract degrees and minutes
        degrees, minutes = map(float, degree_part[:-1].split('°'))
        
        # Convert to decimal degrees
        decimal_degrees = degrees + (minutes / 60)
        return time_part, decimal_degrees
    except Exception:
        raise argparse.ArgumentTypeError(f"Invalid format: '{value}'. Expected format is HH:MM:SS@00°00.0'")

# Function to calculate the mean excluding outliers
def calculate_mean(values):
    degrees = [v[1] for v in values]
    mean_val = mean(degrees)
    stddev_val = stdev(degrees)
    threshold = 2 * stddev_val  # Sets the outlier threshold

    used_values = []
    for v in values:
        if abs(v[1] - mean_val) <= threshold:
            used_values.append((v[0], v[1], '✔'))
        else:
            used_values.append((v[0], v[1], '✘'))

    used_degrees = [v[1] for v in used_values if v[2] == '✔']
    adjusted_mean = mean(used_degrees) if used_degrees else None
    return adjusted_mean, used_values

def main():
    parser = argparse.ArgumentParser(description="Calculate the mean of angular measurements, excluding outliers.")
    parser.add_argument('measurements', type=parse_measurement, nargs='+', help="List of measurements in HH:MM:SS@00°00.0' format")
    args = parser.parse_args()

    mean_value, results = calculate_mean(args.measurements)

    # Display results in console
    headers = ["Time", "Degrees", "Used"]
    print(tabulate(results, headers=headers))
    if mean_value is not None:
        print(f"\nMean of accepted values: {mean_value:.2f}°")
    else:
        print("No values accepted for mean calculation.")

if __name__ == "__main__":
    main()
