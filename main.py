import argparse
import re
from datetime import datetime
from statistics import mean, stdev
from tabulate import tabulate

# Parse function with conversion to decimal degrees
def parse_measurement(value):
    try:
        time_part, degree_part = value.split('@')
        time = datetime.strptime(time_part, '%H:%M:%S')
        
        # Extract degrees and minutes
        degrees, minutes = map(float, degree_part[:-1].split('°'))
        
        # Convert to decimal degrees
        decimal_degrees = degrees + (minutes / 60)
        return time, decimal_degrees
    except Exception:
        raise argparse.ArgumentTypeError(f"Invalid format: '{value}'. Expected format is HH:MM:SS@00°00.0'")

# Parse and separate the operator and value from ignore_slope
def parse_ignore_slope(value):
    if value.startswith(('>', '<')):
        operator = value[0]
        try:
            threshold = float(value[1:])
            return operator, threshold
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid threshold format in '{value}'. Expected format is '<0.001' or '>0.001'")
    else:
        raise argparse.ArgumentTypeError(f"Invalid operator in '{value}'. Expected format is '<value' or '>value'.")

# Function to calculate mean excluding outliers based on slope changes
def calculate_slope_filtered_mean(values, ignore_slope=None):
    # Sort measurements by time
    values.sort(key=lambda x: x[0])

    # Initialize slope lists
    slopes_to = []
    slopes_from = []

    # Calculate "To" and "From" slopes independently
    for i in range(len(values) - 1):
        # Calculate "To" slope (current to next)
        time_diff_to = (values[i+1][0] - values[i][0]).total_seconds()
        degree_diff_to = values[i+1][1] - values[i][1]
        slope_to = degree_diff_to / time_diff_to
        slopes_to.append(slope_to)

    slopes_to.append(None)  # No "to" slope for the last entry

    # Calculate "From" slopes (next to current) for all except the first entry
    slopes_from.append(None)  # No "from" slope for the first entry
    for i in range(1, len(values)):
        time_diff_from = (values[i][0] - values[i-1][0]).total_seconds()
        degree_diff_from = values[i][1] - values[i-1][1]
        slope_from = degree_diff_from / time_diff_from
        slopes_from.append(slope_from)

    # Calculate mean and standard deviation of slopes
    all_slopes = [s for s in slopes_to + slopes_from if s is not None]
    mean_slope = mean(all_slopes)
    stddev_slope = stdev(all_slopes)
    slope_threshold = 2 * stddev_slope  # Define threshold for outliers

    # Unpack ignore_slope operator and threshold
    ignore_operator, ignore_threshold = ignore_slope if ignore_slope else (None, None)

    # Identify outliers based on slope deviation and ignore parameter
    used_values = []
    accepted_slopes = []
    for i, (time, degree) in enumerate(values):
        slope_to = slopes_to[i]
        slope_from = slopes_from[i]

        # Determine if slope_to and slope_from are outliers based on the operator and threshold
        to_outlier = (
            slope_to is not None and abs(slope_to - mean_slope) > slope_threshold or
            (ignore_operator == '>' and slope_to is not None and abs(slope_to) > ignore_threshold) or
            (ignore_operator == '<' and slope_to is not None and abs(slope_to) < ignore_threshold)
        )
        from_outlier = (
            slope_from is not None and abs(slope_from - mean_slope) > slope_threshold or
            (ignore_operator == '>' and slope_from is not None and abs(slope_from) > ignore_threshold) or
            (ignore_operator == '<' and slope_from is not None and abs(slope_from) < ignore_threshold)
        )

        # Mark as outlier if both slopes exist and both are outliers,
        # or if only one slope exists and it is an outlier
        if slope_to is not None and slope_from is not None:
            is_outlier = to_outlier and from_outlier
        else:
            is_outlier = to_outlier or from_outlier

        # Add accepted slopes for mean calculation
        if not to_outlier and slope_to is not None:
            accepted_slopes.append(slope_to)
        if not from_outlier and slope_from is not None:
            accepted_slopes.append(slope_from)

        used_values.append((
            time.strftime('%H:%M:%S'), degree,
            f"{slope_to:+.4f}" if slope_to is not None else "-",  # Display slope with sign
            f"{slope_from:+.4f}" if slope_from is not None else "-",  # Display slope with sign
            '✘' if is_outlier else '✔'
        ))

    # Filter degrees of accepted values and calculate mean of accepted slopes
    accepted_degrees = [v[1] for v in used_values if v[4] == '✔']
    adjusted_mean = mean(accepted_degrees) if accepted_degrees else None
    mean_accepted_slopes = mean(accepted_slopes) if accepted_slopes else None
    return adjusted_mean, mean_accepted_slopes, used_values

def main():
    parser = argparse.ArgumentParser(description="Calculate the mean of angular measurements, excluding steep slope outliers.")
    parser.add_argument('measurements', type=parse_measurement, nargs='+', help="List of measurements in HH:MM:SS@00°00.0' format")
    parser.add_argument('--ignore-slope', type=parse_ignore_slope, help="Threshold with operator in format '<value' or '>value' for ignoring slope values.")
    args = parser.parse_args()

    mean_value, mean_slope_value, results = calculate_slope_filtered_mean(args.measurements, args.ignore_slope)

    # Display results in console
    headers = ["Time", "Degrees", "Slope To (°/s)", "Slope From (°/s)", "Used"]
    formatted_results = [
        (time, f"{degree:.4f}", slope_to, slope_from, used)
        for time, degree, slope_to, slope_from, used in results
    ]
    print(tabulate(formatted_results, headers=headers))
    
    if mean_value is not None:
        print(f"\nMean of accepted values: {mean_value:.4f}°")
    else:
        print("No values accepted for mean calculation.")

    if mean_slope_value is not None:
        print(f"Mean of accepted slopes: {mean_slope_value:.4f}°/s")
    else:
        print("No slopes accepted for mean calculation.")

if __name__ == "__main__":
    main()
