# Sextant Averager 📐🌊

**Sextant Averager** is a command-line tool designed to calculate the average of multiple sextant measurements while excluding extreme outliers. This tool is ideal for sailors, navigators, and anyone analyzing angular measurements from a sextant to get precise data by filtering out inconsistent readings.

## 🧭 Purpose

In celestial navigation, precise sextant readings are critical. This tool lets you input a series of measurements in the format `HH:MM:SS@00°00.0'`. The program calculates the mean of all accepted measurements after excluding outliers, which are identified based on standard deviation. It then outputs a table showing which values were accepted (`✔`) or excluded (`✘`), along with the calculated average of the accepted measurements.

## ⚙️ Usage

### Prerequisites

- Python 3.x is required to run this program.

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/sextant-averager.git
   cd sextant-averager
   ```

2. (Optional) Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use venv\Scripts\activate
   ```

### Running the Program

1. To use the tool, enter your measurements in the format `HH:MM:SS@00°00.0'` as command-line arguments. For example:
   ```bash
   python main.py 12:15:30@05°30.2' 12:16:30@05°30.0' 12:17:30@05°35.1'
   ```

2. The program will display a table like this:

   ```
   | Time       | Degrees | Used |
   |------------|---------|------|
   | 12:15:30   | 5.30    | ✔    |
   | 12:16:30   | 5.30    | ✔    |
   | 12:17:30   | 5.35    | ✘    |

   Mean of accepted values: 5.30°
   ```

3. **Outliers** are flagged with `✘`, and only accepted values (`✔`) contribute to the calculated mean. The final average, excluding outliers, is shown below the table.

## 👤 Author

Created by [Kevin Veen-Birkenbach](https://veen.world). 

For more information about my nautical and yachtmaster services, visit 🌐 [yachtmaster.world](https://yachtmaster.world/).  
For details about my IT solutions, check out 🌐 [cybermaster.space](https://cybermaster.space/).

This project was created with the assistance of AI. The conversation you will find [here](https://chatgpt.com/share/671d55a5-3a5c-800f-8330-fbcbd9c5261c).

## 📜 License

This software is licensed under the **[GNU Affero General Public License, Version 3](./LICENSE)**.
