import argparse
import re
from datetime import datetime
from statistics import mean, stdev
from tabulate import tabulate

# DEFAULT_IGNORE_SLOPE sets a conservative threshold to filter out unrealistic altitude rate changes.
DEFAULT_IGNORE_SLOPE = ">0.005"
DEFAULT_TOLERANCE = 10  # Default tolerance as a percentage


class Measurement:
    def __init__(self, time, degrees, slope_to=None, slope_from=None):
        self.time = time
        self.degrees = degrees
        self.slope_to = slope_to
        self.slope_from = slope_from
        self.slope_ok = False
        self.tolerance_ok = False

    def set_slopes(self, slope_to, slope_from):
        self.slope_to = slope_to
        self.slope_from = slope_from

    def check_slope_ok(self, mean_slope, slope_threshold, ignore_operator, ignore_threshold):
        to_within_threshold = (self.slope_to is not None and abs(self.slope_to - mean_slope) <= slope_threshold) and \
                            ((ignore_operator == '>' and abs(self.slope_to) <= ignore_threshold) or \
                            (ignore_operator == '<' and abs(self.slope_to) >= ignore_threshold))

        from_within_threshold = (self.slope_from is not None and abs(self.slope_from - mean_slope) <= slope_threshold) and \
                                ((ignore_operator == '>' and abs(self.slope_from) <= ignore_threshold) or \
                                (ignore_operator == '<' and abs(self.slope_from) >= ignore_threshold))

        # Slope OK if at least one of the slopes (To or From) is within threshold
        self.slope_ok = to_within_threshold or from_within_threshold


    def check_tolerance_ok(self, mean_slope_ok, tolerance_threshold):
        if self.slope_ok:
            to_within_tolerance = self.slope_to is not None and abs(self.slope_to - mean_slope_ok) <= tolerance_threshold
            from_within_tolerance = self.slope_from is not None and abs(self.slope_from - mean_slope_ok) <= tolerance_threshold
            self.tolerance_ok = to_within_tolerance and from_within_tolerance  # Use AND condition here


def parse_measurement(value):
    try:
        time_part, degree_part = value.split('@')
        time = datetime.strptime(time_part, '%H:%M:%S')
        degrees, minutes = map(float, degree_part[:-1].split('°'))
        decimal_degrees = degrees + (minutes / 60)
        return Measurement(time, decimal_degrees)
    except Exception:
        raise argparse.ArgumentTypeError(f"Invalid format: '{value}'. Expected format is HH:MM:SS@00°00.0'")


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


def calculate_slopes(measurements):
    for i in range(len(measurements) - 1):
        time_diff = (measurements[i + 1].time - measurements[i].time).total_seconds()
        degree_diff = measurements[i + 1].degrees - measurements[i].degrees
        slope_to = degree_diff / time_diff
        measurements[i].slope_to = slope_to
        measurements[i + 1].slope_from = slope_to


def calculate_mean_slope_ok(measurements, ignore_slope, tolerance):
    slopes = [m.slope_to for m in measurements if m.slope_to is not None] + \
             [m.slope_from for m in measurements if m.slope_from is not None]
    mean_slope = mean(slopes)
    stddev_slope = stdev(slopes)
    slope_threshold = 2 * stddev_slope

    ignore_operator, ignore_threshold = ignore_slope

    # Mark slope OK status based on ignore_slope and calculated thresholds
    for m in measurements:
        m.check_slope_ok(mean_slope, slope_threshold, ignore_operator, ignore_threshold)

    accepted_slopes = [s for s in slopes if s is not None and abs(s - mean_slope) <= slope_threshold]
    mean_slope_ok = mean(accepted_slopes) if accepted_slopes else None
    tolerance_threshold = mean_slope_ok * (tolerance / 100) if mean_slope_ok else None

    return mean_slope_ok, tolerance_threshold


def main():
    parser = argparse.ArgumentParser(description="Calculate the mean of angular measurements, excluding steep slope outliers.")
    parser.add_argument('measurements', type=parse_measurement, nargs='+', help="List of measurements in HH:MM:SS@00°00.0' format")
    parser.add_argument('--ignore-slope', type=parse_ignore_slope, default=DEFAULT_IGNORE_SLOPE, help=f"Threshold with operator in format '<value' or '>value' for ignoring slope values. Default is {DEFAULT_IGNORE_SLOPE}.")
    parser.add_argument('--tolerance', type=float, default=DEFAULT_TOLERANCE, help=f"Tolerance in percentage for slope deviation from the mean slope. Default is {DEFAULT_TOLERANCE}%.")
    args = parser.parse_args()

    measurements = args.measurements
    calculate_slopes(measurements)

    mean_slope_ok, tolerance_threshold = calculate_mean_slope_ok(measurements, args.ignore_slope, args.tolerance)

    # Apply tolerance check
    for m in measurements:
        m.check_tolerance_ok(mean_slope_ok, tolerance_threshold)

    # Display results
    headers = ["Time", "Degrees", "Slope To (°/s)", "Slope From (°/s)", "Slope OK", "Tolerance OK"]
    table_data = [
        (
            m.time.strftime('%H:%M:%S'), f"{m.degrees:.4f}",
            f"{m.slope_to:+.4f}" if m.slope_to is not None else "-",
            f"{m.slope_from:+.4f}" if m.slope_from is not None else "-",
            '✔' if m.slope_ok else '✘',
            '✔' if m.tolerance_ok else '✘'
        )
        for m in measurements
    ]
    print(tabulate(table_data, headers=headers))

    # Summary
    accepted_values = [m.degrees for m in measurements if m.slope_ok]
    mean_value = mean(accepted_values) if accepted_values else None
    if mean_value is not None:
        print(f"\nMean of accepted values: {mean_value:.4f}°")
    else:
        print("No values accepted for mean calculation.")

    print(f"Mean of Slope OK slopes: {mean_slope_ok:.4f}°/s" if mean_slope_ok else "No slopes within tolerance for mean calculation.")
    print(f"Ignore slope threshold used: {args.ignore_slope}")
    print(f"Tolerance: <{args.tolerance}%")

if __name__ == "__main__":
    main()
