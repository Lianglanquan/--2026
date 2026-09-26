#ifndef WHEELBOT_MISSION_CLIENT_H
#define WHEELBOT_MISSION_CLIENT_H

#include <cstdint>
#include <expected>
#include <string>

class WheelbotMissionClient {
public:
    std::expected<std::string, std::string> Submit(const std::string& task_type,
                                                   const std::string& target_location,
                                                   const std::string& target_item,
                                                   const std::string& return_location);
    std::expected<std::string, std::string> GetStatus(const std::string& mission_id);
    std::expected<std::string, std::string> Cancel(const std::string& mission_id);

private:
    std::string last_fingerprint_;
    std::string last_request_id_;
    int64_t last_request_us_ = 0;

    std::expected<std::string, std::string> Request(const std::string& method,
                                                    const std::string& path,
                                                    std::string content = {});
    static std::string NewRequestId();
};

#endif  // WHEELBOT_MISSION_CLIENT_H
