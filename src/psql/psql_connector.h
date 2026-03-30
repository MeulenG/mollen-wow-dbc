#ifndef PSQL_CONNECTOR_H
#define PSQL_CONNECTOR_H

#include <string>
#include <vector>
#include <pqxx/pqxx>
#include <iostream>

class psql_connector
{
private:
    const std::string invalidCataLogName = "3D000";
    const std::string duplicateDatabaseName = "42P04";
    const std::string numericValueOutOfRange = "22003";

public:
    void DatabaseConnect(const std::string& dbname, const std::string& user, const std::string& password, const std::string& host, int port);
    int StartTransaction(pqxx::connection);
};

#endif // PSQL_CONNECTOR_H
