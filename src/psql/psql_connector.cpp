#include "psql_connector.h"

void psql_connector::DatabaseConnect(const std::string& dbname, const std::string& user, const std::string& password, const std::string& host, int port)
{    
    try {
        std::string connection_str = "dbname=" + dbname + " user=" + user + " password=" + password + " host=" + host + " port=" + std::to_string(port);
        pqxx::connection c(connection_str);
        if (c.is_open()) {
            std::cout << "Connected to database successfully: " << c.dbname() << std::endl;
        } else {
            std::cerr << "Failed to connect to database" << std::endl;
        }
    } catch (const pqxx::sql_error& e) {
        std::cerr << "SQL error: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

int StartTransaction(pqxx::connection) {
    return 1;
}
