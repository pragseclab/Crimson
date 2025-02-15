


#!/bin/bash

# Usage check
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

search_dir=$1  # Directory to search in, provided as an argument

# Define the text file to write the results
results_file="$search_dir/iocs_results"
processed_files_log="$search_dir/iocs_results.log"

# Clear the results file or create it if it doesn't exist
: > "$results_file"

# Ensure processed files log exists
touch "$processed_files_log"

# Specify the IOC types to search for
ioc_types=(bitcoin bitcoincash cardano dashcoin dogecoin ethereum litecoin monero ripple tezos tronix zcash webmoney onionAddress email phoneNumber facebookHandle githubHandle instagramHandle linkedinHandle pinterestHandle telegramHandle twitterHandle whatsappHandle youtubeHandle youtubeChannel)

 target_options=""
for ioc_type in "${ioc_types[@]}"; do
    target_options+="-t $ioc_type "
done

 if [ ! -d "$search_dir" ]; then
    echo "The specified path is not a directory: $search_dir" | tee -a "$results_file"
    exit 2
fi

# Iterate over HTML files in the directory and subdirectories and perform searches
find "$search_dir" -type f -name '*.html' | while read html_file; do
    # Check if the file has been processed already
    if grep -Fxq "$html_file" "$processed_files_log"; then
        echo "Skipping already processed file: $html_file"
    else
        echo "Searching IOCs in $html_file" | tee -a "$results_file"
        # Execute iocsearcher on each HTML file and append output to the results file
        iocsearcher -f "$html_file" -F $target_options 2>&1 | tee -a "$results_file"
        echo "---------------------------------------" | tee -a "$results_file"
        # Log that this file has been processed
        echo "$html_file" >> "$processed_files_log"
    fi
done

echo "All IOC searches completed." | tee -a "$results_file"