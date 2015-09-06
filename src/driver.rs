use std::process::{Command,Child,Stdio};
use std::io::prelude::*;
use std::io::BufReader;
use std::fs::File;
use std::os::unix::io::{FromRawFd,AsRawFd};
use std::collections::HashMap;
use libc::funcs::posix88::unistd::close;

pub struct Driver {
    child : Child,
    reader: BufReader<File>,
}

bitflags! {
    flags Protocols : u32 {
        const TEXT =        0b00000,
        const BIN =         0b00001,
        const COMPRESSED =  0x00100,
        const ENCRYPRED =   0x01000,
        const SIGNED =      0x10000,
    }
}


impl Driver {
    pub fn start(cmd : &str) -> Driver {
        let child = Command::new(cmd)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
            .unwrap_or_else(|e|panic!("failed to start process {}: {}", cmd, e));

        // Hack because we can't create the reader from stdout since it would require to move child
        // as well...
        let stdout_fd = child.stdout.as_ref().unwrap().as_raw_fd();
        let reader = unsafe{ BufReader::new(File::from_raw_fd(stdout_fd)) };
        let mut driver = Driver {
            child: child,
            reader: reader
        };

        driver.handshake();
        driver
    }

    pub fn handshake(&mut self) -> Protocols {
        let mut protocols = String::new();
        self.reader.read_line(&mut protocols).unwrap();
        let protocols_bits = protocols.trim().parse().unwrap_or_else(|e|panic!("invalid handshake '{}': {}", protocols, e));
        Protocols::from_bits(protocols_bits).unwrap()
    }

    pub fn send_request(&mut self, mission : u32, data : &str) -> u32 {
        use rand;

        let request_id = rand::random::<u32>();
        let packet = format!("{:x}:{}:{}\n", request_id, mission, data);

        self.child.stdin.as_mut().unwrap().write(packet.as_bytes()).unwrap();

        request_id
    }

    pub fn collect_response(self) -> HashMap<u32,String> {
        self.reader.lines()
            .map(|x|x.unwrap())
            .map(|response| {
                let mut data = response.split(':');
                (u32::from_str_radix(data.next().unwrap(), 16).unwrap(), data.next().unwrap().to_string())
            })
            .collect()
    }

    pub fn close_stdin(&self) {
        unsafe { close(self.child.stdin.as_ref().unwrap().as_raw_fd()); }
    }
}

