#include <catch2/catch_session.hpp>

#include <cstdlib>
#include <iostream>

int main(int argc, char* argv[]) {
    int result = Catch::Session().run(argc, argv);

    // vcpkg's debug pqxx.dll access-violates during DLL unload at process
    // shutdown (libpq/OpenSSL atexit cleanup) - even under --list-tests,
    // which made ctest discovery report the whole suite as crashed. All
    // assertions have already run at this point; skip static/DLL teardown
    // so the exit code reflects the tests, not the dependency's shutdown
    // bug. Streams flushed manually because _Exit skips that too.
    std::cout.flush();
    std::cerr.flush();
    std::_Exit(result);
}
