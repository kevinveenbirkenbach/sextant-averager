import argparse
import re
from datetime import datetime
from statistics import mean, stdev
from tabulate import tabulate

# DEFAULT_IGNORE_SLOPE sets a conservative threshold to filter out
# unrealistically high altitude rate changes (°/s) due to measurement
# noise or error. The value ">0.005" was chosen based on the maximum
# apparent rate of altitude change caused by Earth's rotation (~0.0042°/s),
# plus allowances for atmospheric refraction, parallax (especially for the Moon),
# and observer height. This threshold ensures realistic rates for natural objects
# like the Sun, Moon, planets, and stars are retained, while filtering
# spurious values.
DEFAULT_IGNORE_SLOPE = ">0.005"
DEFAULT_TOLERANCE = 10  # Default tolerance as a percentage

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

# Function to calculate mean excluding outliers based on slope changes and tolerance
def calculate_slope_filtered_mean(values, ignore_slope=None, tolerance=DEFAULT_TOLERANCE):
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

    # Calculate tolerance threshold
    tolerance_threshold = mean_slope * (tolerance / 100)

    # Unpack ignore_slope operator and threshold
    ignore_operator, ignore_threshold = ignore_slope if ignore_slope else parse_ignore_slope(DEFAULT_IGNORE_SLOPE)

    # Identify outliers based on slope deviation, ignore parameter, and tolerance
    used_values = []
    accepted_slopes_to = []
    accepted_slopes_from = []
    tolerance_accepted_slopes = []

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

        # Check if within tolerance
        to_within_tolerance = slope_to is not None and abs(slope_to - mean_slope) <= tolerance_threshold
        from_within_tolerance = slope_from is not None and abs(slope_from - mean_slope) <= tolerance_threshold

        # Mark as outlier if both slopes exist and both are outliers,
        # or if only one slope exists and it is an outlier
        is_outlier = (slope_to is not None and slope_from is not None and to_outlier and from_outlier) or \
                     (slope_to is not None and slope_from is None and to_outlier) or \
                     (slope_from is not None and slope_to is None and from_outlier)

        # Add accepted slopes for mean calculation
        if not to_outlier and slope_to is not None:
            accepted_slopes_to.append(slope_to)
        if not from_outlier and slope_from is not None:
            accepted_slopes_from.append(slope_from)

        # Add to tolerance-accepted slopes list if within tolerance
        if to_within_tolerance and slope_to is not None:
            tolerance_accepted_slopes.append(slope_to)
        if from_within_tolerance and slope_from is not None:
            tolerance_accepted_slopes.append(slope_from)

        used_values.append((
            time.strftime('%H:%M:%S'), degree,
            f"{slope_to:+.4f}" if slope_to is not None else "-",  # Display slope with sign
            f"{slope_from:+.4f}" if slope_from is not None else "-",  # Display slope with sign
            '✔' if not is_outlier else '✘',
            '✔' if to_within_tolerance and from_within_tolerance else '✘'
        ))

    # Filter degrees of accepted values and calculate mean of accepted slopes
    accepted_degrees = [v[1] for v in used_values if v[4] == '✔']
    adjusted_mean = mean(accepted_degrees) if accepted_degrees else None
    mean_accepted_slope_to = mean(accepted_slopes_to) if accepted_slopes_to else None
    mean_accepted_slope_from = mean(accepted_slopes_from) if accepted_slopes_from else None
    mean_tolerance_accepted_slope = mean(tolerance_accepted_slopes) if tolerance_accepted_slopes else None

    return adjusted_mean, mean_accepted_slope_to, mean_accepted_slope_from, mean_tolerance_accepted_slope, used_values, f"{ignore_operator}{ignore_threshold}", tolerance

def main():
    parser = argparse.ArgumentParser(description="Calculate the mean of angular measurements, excluding steep slope outliers.")
    parser.add_argument(
        'measurements', 
        type=parse_measurement, 
        nargs='+', 
        help="List of measurements in HH:MM:SS@00°00.0' format"
    )
    parser.add_argument(
        '--ignore-slope', 
        type=parse_ignore_slope, 
        default=DEFAULT_IGNORE_SLOPE, 
        help=f"Threshold with operator in format '<value' or '>value' for ignoring slope values. Default is {DEFAULT_IGNORE_SLOPE}."
    )
    parser.add_argument(
        '--tolerance',
        type=float,
        default=DEFAULT_TOLERANCE,
        help=f"Tolerance in percentage for slope deviation from the mean slope. Default is {DEFAULT_TOLERANCE}%."
    )
    args = parser.parse_args()

    mean_value, mean_slope_to, mean_slope_from, mean_tolerance_slope, results, ignore_slope_used, tolerance = calculate_slope_filtered_mean(
        args.measurements, args.ignore_slope, args.tolerance)

    # Display results in console
    headers = ["Time", "Degrees", "Slope To (°/s)", "Slope From (°/s)", "Slope OK", "Tolerance OK"]
    formatted_results = [
        (time, f"{degree:.4f}", slope_to, slope_from, used, tol_ok)
        for time, degree, slope_to, slope_from, used, tol_ok in results
    ]
    print(tabulate(formatted_results, headers=headers))
    
    # Output mean of accepted degrees and slopes
    if mean_value is not None:
        print(f"\nMean of accepted values: {mean_value:.4f}°")
    else:
        print("No values accepted for mean calculation.")

    if mean_slope_to is not None:
        print(f"Mean of accepted Slope To values: {mean_slope_to:.4f}°/s")
    else:
        print("No Slope To values accepted for mean calculation.")

    if mean_slope_from is not None:
        print(f"Mean of accepted Slope From values: {mean_slope_from:.4f}°/s")
    else:
        print("No Slope From values accepted for mean calculation.")

    if mean_tolerance_slope is not None:
        print(f"Mean of Tolerance OK slopes: {mean_tolerance_slope:.4f}°/s")
    else:
        print("No slopes within tolerance for mean calculation.")

    # Output the used ignore slope threshold and tolerance
    print(f"Ignore slope threshold used: {ignore_slope_used}°/s")
    print(f"Tolerance: <{tolerance}%")

if __name__ == "__main__":
    main()
