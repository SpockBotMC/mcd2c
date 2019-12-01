# CMake generated Testfile for 
# Source directory: /home/vito/code/mcd2c/cNBT
# Build directory: /home/vito/code/mcd2c/cNBT
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(test_hello_world "bin/check" "/home/vito/code/mcd2c/cNBT/testdata/hello_world.nbt")
add_test(test_simple_level "bin/check" "/home/vito/code/mcd2c/cNBT/testdata/simple_level.nbt")
add_test(test_issue_13 "bin/check" "/home/vito/code/mcd2c/cNBT/testdata/issue_13.nbt")
add_test(test_issue_18 "bin/check" "/home/vito/code/mcd2c/cNBT/testdata/issue_18.nbt")
add_test(test_afl "/home/vito/code/mcd2c/cNBT/afl_check.sh" "bin/afl_check")
