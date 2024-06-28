# Domain Analysis Tool

This Python script performs a comprehensive analysis of a given domain, gathering various types of information and generating a detailed PDF report.

## Features

- Fetches and analyzes web content
- Extracts links from the webpage
- Retrieves domain registration information
- Performs DNS lookups (A records)
- Checks MX records
- Performs reverse DNS lookups
- Provides IP geolocation information
- Generates a comprehensive PDF report

## Requirements

- Python 3.6+
- Required Python packages (see requirements.txt)
- Internet connection for data retrieval

## Installation

1. Clone the repository:

```
git clone https://github.com/Frontsightvc/domain_analysis.git 

cd domain_analysis
```

2. Install the required packages:

```
pip install -r requirements.txt
```


## Usage

### Local Usage

Run the script from the command line, providing a domain name as an argument:

``` 
python domain_analysis_tool.py example.com
```


The script will generate a 'report.pdf' file in the same directory.

### Google Colab Usage

1. Open a new Google Colab notebook.

2. Run the following commands in a code cell:

```
!git clone https://github.com/Frontsightvc/domain_analysis.git
%cd domain_analysis
!pip install -r requirements.txt
```


3. Run the script:

```
!python domain_analysis.py example.com
```

## How It Works

URL Formatting: The script ensures the input URL has a proper scheme (http:// or https://).

Web Content Retrieval: It fetches the HTML content of the specified URL.

HTML Parsing: The script extracts links and text content from the HTML.

Domain Information: It retrieves WHOIS information for the domain.

DNS Information: The script performs DNS lookups to get A records.

MX Records: It checks for MX (mail exchanger) records.

Reverse DNS: The script performs a reverse DNS lookup on the IP address.

Geolocation: It provides geolocation information for the IP address.

PDF Generation: All gathered information is compiled into a structured PDF report.


