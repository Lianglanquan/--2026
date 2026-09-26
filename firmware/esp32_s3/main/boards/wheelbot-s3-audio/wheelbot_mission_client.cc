#include "wheelbot_mission_client.h"

#include <cstdio>
#include <utility>

#include <cJSON.h>
#include <esp_random.h>
#include <esp_timer.h>
#include <http.h>

#include "boards/common/board.h"
#include "cjson_utils.h"

namespace {

std::string JsonString(cJSON* root) {
    CJsonStringUniquePtr encoded(cJSON_PrintUnformatted(root));
    return encoded ? std::string(encoded.get()) : std::string();
}

}  // namespace

std::expected<std::string, std::string> WheelbotMissionClient::Request(
    const std::string& method, const std::string& path, std::string content) {
    const std::string token = CONFIG_WHEELBOT_MISSION_TOKEN;
    if (token.empty()) {
        return std::unexpected("WheelBot mission token is not configured");
    }

    auto network = Board::GetInstance().GetNetwork();
    if (network == nullptr) {
        return std::unexpected("network is unavailable");
    }
    auto http = network->CreateHttp(3);
    http->SetHeader("Accept", "application/json");
    http->SetHeader("Content-Type", "application/json");
    http->SetHeader("Authorization", "Bearer " + token);
    if (!content.empty()) {
        http->SetContent(std::move(content));
    }

    std::string url = CONFIG_WHEELBOT_MISSION_BASE_URL;
    if (!url.empty() && url.back() == '/') {
        url.pop_back();
    }
    url += path;
    if (auto opened = http->Open(method, url); !opened) {
        return std::unexpected("mission API connection failed: " + opened.error().ToString());
    }
    auto status = http->GetStatusCode();
    if (!status) {
        http->Close();
        return std::unexpected("mission API status failed: " + status.error().ToString());
    }
    std::string body = http->ReadAll();
    http->Close();
    if (*status < 200 || *status >= 300) {
        return std::unexpected("mission API returned HTTP " + std::to_string(*status) + ": " +
                               body);
    }
    return body;
}

std::string WheelbotMissionClient::NewRequestId() {
    char value[32];
    std::snprintf(value, sizeof(value), "xiaozhi-%08lx-%08lx",
                  static_cast<unsigned long>(esp_random()),
                  static_cast<unsigned long>(esp_random()));
    return value;
}

std::expected<std::string, std::string> WheelbotMissionClient::Submit(
    const std::string& task_type, const std::string& target_location,
    const std::string& target_item, const std::string& return_location) {
    CJsonUniquePtr root(cJSON_CreateObject());
    if (!root) {
        return std::unexpected("failed to allocate mission request");
    }
    const std::string fingerprint = task_type + "\n" + target_location + "\n" + target_item +
                                    "\n" + return_location;
    const int64_t now_us = esp_timer_get_time();
    if (fingerprint != last_fingerprint_ || now_us - last_request_us_ > 30000000LL) {
        last_fingerprint_ = fingerprint;
        last_request_id_ = NewRequestId();
    }
    last_request_us_ = now_us;
    cJSON_AddStringToObject(root.get(), "request_id", last_request_id_.c_str());
    cJSON_AddStringToObject(root.get(), "task_type", task_type.c_str());
    cJSON_AddStringToObject(root.get(), "target_location", target_location.c_str());
    cJSON_AddStringToObject(root.get(), "target_item", target_item.c_str());
    cJSON_AddStringToObject(root.get(), "return_location", return_location.c_str());
    return Request("POST", "/api/v1/missions", JsonString(root.get()));
}

std::expected<std::string, std::string> WheelbotMissionClient::GetStatus(
    const std::string& mission_id) {
    if (mission_id.empty()) {
        return Request("GET", "/api/v1/missions/current");
    }
    return Request("GET", "/api/v1/missions/" + mission_id);
}

std::expected<std::string, std::string> WheelbotMissionClient::Cancel(
    const std::string& mission_id) {
    if (mission_id.empty()) {
        return std::unexpected("mission_id is required");
    }
    return Request("POST", "/api/v1/missions/" + mission_id + "/cancel", "{}");
}
