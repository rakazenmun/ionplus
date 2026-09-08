#include <iostream>
#include <fstream>
#include <string>
#include <thread>
#include <chrono>

using namespace std;

void process_data() {
    ifstream fin("input.json");
    if (!fin.is_open()) {
        cout << "input.json not found, skipping iteration..." << endl;
        return;
    }

    // Read JSON file into string
    string raw_input((istreambuf_iterator<char>(fin)), istreambuf_iterator<char>());
    fin.close();

    // Read state from last_seen.txt
    string last_seen = "";
    ifstream history_in("last_seen.txt");
    if (history_in.is_open()) {
        getline(history_in, last_seen);
        history_in.close();
    }

    // Helper lambda to extract JSON fields
    auto get_field = [&](const string& key) {
        size_t pos = raw_input.find("\"" + key + "\"");
        if (pos == string::npos) return string("");
        pos = raw_input.find(":", pos);
        if (pos == string::npos) return string("");
        size_t start = raw_input.find_first_of("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", pos);
        size_t end = raw_input.find_first_of(",}\"\n\r", start);
        if (start == string::npos || end == string::npos) return string("");
        return raw_input.substr(start, end - start);
    };

    string current_id = get_field("id");
    string title = get_field("title");
    string body = get_field("body");
    string author = get_field("author");

    // Fallback test values if API returns empty JSON
    if (current_id.empty()) {
        current_id = "test_1001";
        title = "Test"; 
        body = "Hello World!";
        author = "William Nguyen";
    }

    // Combine values into a pipe-delimited string: TITLE|AUTHOR|BODY
    string formatted_text = title + "|" + author + "|" + body;

    // Output logic
    ofstream fout("output.txt");
    if (!current_id.empty() && current_id != last_seen) {
        fout << formatted_text;

        ofstream history_out("last_seen.txt");
        history_out << current_id;
        history_out.close();
    } else {
        fout << "NONE";
    }
    fout.close();
}

int main() {
    while (true) {
        process_data();
        
        // Sleep for 60 seconds between checks
        this_thread::sleep_for(chrono::seconds(60));
    }

    return 0;
}