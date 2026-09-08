#include <iostream>
#include <fstream>
#include <string>
#include <sstream>

// Basic lightweight helper to extract string values from a simple JSON structure
std::string extractJsonValue(const std::string& json, const std::string& key) {
    std::string searchKey = "\"" + key + "\":";
    size_t startPos = json.find(searchKey);
    if (startPos == std::string::npos) return "";

    startPos += searchKey.length();
    // Skip whitespace and opening quote
    while (startPos < json.length() && (json[startPos] == ' ' || json[startPos] == '"')) {
        startPos++;
    }

    size_t endPos = json.find("\"", startPos);
    if (endPos == std::string::npos) return "";

    return json.substr(startPos, endPos - startPos);
}

void process_data() {
    std::ifstream inFile("input.json");
    if (!inFile.is_open()) {
        std::cerr << "Error opening input.json" << std::endl;
        return;
    }

    std::stringstream buffer;
    buffer << inFile.rdbuf();
    std::string jsonStr = buffer.str();
    inFile.close();

    std::string id = extractJsonValue(jsonStr, "id");
    std::string title = extractJsonValue(jsonStr, "title");
    std::string author = extractJsonValue(jsonStr, "author");
    std::string body = extractJsonValue(jsonStr, "body");

    // Read the last processed ID
    std::string lastId = "";
    std::ifstream lastIdFile("last_id.txt");
    if (lastIdFile.is_open()) {
        std::getline(lastIdFile, lastId);
        lastIdFile.close();
    }

    std::ofstream outFile("output.txt");
    if (!outFile.is_open()) {
        std::cerr << "Error opening output.txt" << std::endl;
        return;
    }

    // Check if this announcement is new
    if (!id.empty() && id != lastId) {
        outFile << title << "|" << author << "|" << body;
        
        // Update last processed ID
        std::ofstream updateLastId("last_id.txt");
        if (updateLastId.is_open()) {
            updateLastId << id;
            updateLastId.close();
        }
    } else {
        outFile << "NONE";
    }

    outFile.close();
}

int main() {
    process_data();
    return 0;
}