#[macro_use]
extern crate bitflags;
extern crate byteorder;
extern crate libc;
extern crate getopts;
extern crate rustc_serialize;
extern crate rand;

use rustc_serialize::json;
use getopts::Options;
use std::env;
use std::path::Path;
use std::fs::File;
use std::error::Error;
use std::collections::{HashSet};

mod driver;
mod packet;

use driver::Driver;

#[derive(PartialEq)]
enum Result {
    Succeed,
    Timeout,
    Failed
}

struct TestResult<'a> {
    test_data : &'a TestData,
    id : u32,
    result : Result
}

struct MissionResults<'a> {
    mission : &'a MissionData,
    tests : Vec<TestResult<'a>>
}

struct TestsResult<'a> {
    missions : Vec<MissionResults<'a>>,
}

#[derive(RustcDecodable)]
struct TestData {
    request : String,
    expected : String
}

#[derive(RustcDecodable)]
struct MissionData {
    id : u32,
    name : String,
    tests: Vec<TestData>
}

#[derive(RustcDecodable)]
struct TestsData {
    missions : Vec<MissionData>
}

impl TestsData {
    fn parse(filepath : &Path) -> TestsData {
        use std::io::Read;

        let str_path = filepath.to_string_lossy();
        let mut file = match File::open(&filepath) {
            Err(why) => panic!("couldn't open {}: {}", str_path, Error::description(&why)),
            Ok(file) => file,
        };

        let mut s = String::new();
        match file.read_to_string(&mut s) {
            Err(why) => panic!("couldn't read {}: {}", str_path, Error::description(&why)),
            Ok(_) => (),
        };

        match json::decode(&s) {
            Err(why) => panic!("couldn't parse {}: {}", str_path, Error::description(&why)),
            Ok(tests) => tests,
        }
    }

    fn run_tests<'a>(self : &'a TestsData, mut driver : Driver, ids : &HashSet<u32>) -> TestsResult<'a> {
        let filtered_mission = self.missions.iter().filter(|&m|ids.contains(&m.id));

        let mut results = TestsResult::from_missions(filtered_mission.collect());

        for mission_results in &mut results.missions {
            for test in &mut mission_results.tests {
                test.id = driver.send_request(mission_results.mission.id, &test.test_data.request)
            }
        }

        driver.close_stdin();
        let responses = driver.collect_response();

        for mission_results in &mut results.missions {
            for test in &mut mission_results.tests {
                match responses.get(&test.id) {
                    Some(response) => {
                        test.result =
                            if *response == test.test_data.expected {
                                Result::Succeed
                            } else {
                                Result::Failed
                            }
                    },
                    None => ()
                }
            }
        }

        results
    }

}

impl <'a>TestsResult<'a> {
    fn from_missions(test_data : Vec<&'a MissionData>) -> TestsResult<'a> {
        TestsResult {
            missions: test_data.iter().map(|m| MissionResults::from_mission(m)).collect()
        }
    }

    fn print(&self) {
        println!("Results:");
        for mission in &self.missions {
            let succeed = mission.tests.iter().filter(|&t|t.result == Result::Succeed).count();
            let failed = mission.tests.iter().filter(|&t|t.result == Result::Failed).count();
            let timeout = mission.tests.iter().filter(|&t|t.result == Result::Timeout).count();
            print!("{}: {} Succeed, {} Failed, {} Timeout\n",
                   mission.mission.name,
                   succeed, failed, timeout)
        }
    }
}

impl <'a>MissionResults<'a> {
    fn from_mission(mission : &'a MissionData) -> MissionResults {
        MissionResults {
            mission: mission,
            tests: mission.tests.iter().map(|t| {
                TestResult {
                    test_data: &t,
                    id: 0,
                    result: Result::Timeout
                }
            }).collect()
        }
    }
}

fn print_usage(program: &str, opts: Options) {
    let brief = format!("Usage: {} PROGRAM [options]", program);
    print!("{}", opts.usage(&brief));
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let program = args[0].clone();

    let mut opts = Options::new();
    opts.reqopt("t", "testfile", "set test file", "FILE");
    opts.optmulti("i", "includes", "set the included tests id", "ID");
    opts.optflag("h", "help", "print this help menu");

    let matches = match opts.parse(&args[1..]) {
        Ok(m) => { m }
        Err(f) => {
            println!("{}", Error::description(&f));
            print_usage(&program, opts);
            return;
        }
    };

    if matches.opt_present("h") {
        print_usage(&program, opts);
        return;
    }

    let program_file = if matches.free.len() == 1 {
        matches.free[0].clone()
    } else {
        print_usage(&program, opts);
        return;
    };

    let test_file = matches.opt_str("t").unwrap();
    let mut ids : HashSet<u32> = matches.opt_strs("i").iter().map(|i|i.trim().parse::<u32>().unwrap()).collect();
    if ids.len() == 0 {
        ids.extend(1..11);
    }

    let test_data = TestsData::parse(Path::new(&test_file));
    let driver = Driver::start(&program_file);
    let result = test_data.run_tests(driver, &ids);
    result.print()
}

