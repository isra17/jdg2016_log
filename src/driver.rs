use std::process::{Command,Child,Stdio};
use std::io::prelude::*;
use std::io::{Cursor,BufReader};
use std::fs::File;
use std::os::unix::io::{FromRawFd,AsRawFd};
use std::collections::HashMap;
use libc::funcs::posix88::unistd::close;
use byteorder::{LittleEndian,ReadBytesExt,WriteBytesExt};

use packet::Packet;

pub struct Driver {
    child : Child,
    reader: BufReader<File>,
    protocols : Protocols,
}

pub struct Response {
    id : u32,
    data : String
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

impl Response {
    fn parse(data : Vec<u8>, protocols : Protocols) -> Response {
        if protocols.contains(BIN) {
            let mut cursor = Cursor::new(data);
            let id = cursor.read_u32::<LittleEndian>().unwrap();
            let mut answer = String::new();
            cursor.read_to_string(&mut answer);
            Response{id:id, data:answer}
        } else {
            let str_data = String::from_utf8(data).unwrap();
            let mut split = str_data.split(':');
            let id = u32::from_str_radix(split.next().unwrap(), 16).unwrap();
            let answer = split.next().unwrap();
            Response{id:id, data:answer.to_string()}
        }
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
            reader: reader,
            protocols: TEXT,
        };

        driver.handshake();
        driver
    }

    pub fn handshake(&mut self) -> Protocols {
        let mut protocols = String::new();
        self.reader.read_line(&mut protocols).unwrap();
        let protocols_bits = protocols.trim().parse().unwrap_or_else(|e|panic!("invalid handshake '{}': {}", protocols, e));
        self.protocols = Protocols::from_bits(protocols_bits).unwrap();
        self.protocols
    }

    pub fn send_request(&mut self, mission : u32, data : &str) -> u32 {
        use rand;

        let request_id = rand::random::<u32>();
        let packet = format!("{:0>8x}:{}:{}\n", request_id, mission, data);

        self.child.stdin.as_mut().unwrap().write(packet.as_bytes()).unwrap();

        request_id
    }

    pub fn collect_response(mut self) -> HashMap<u32,String> {
        let mut responses = HashMap::new();
        loop {
            let packet = self.read_packets();
            if packet.is_empty() {
                break
            }

            // Parse response
            let response = Response::parse(packet.into_bytes(), self.protocols);
            responses.insert(response.id, response.data);
        }

        responses
    }

    pub fn close_stdin(&self) {
        unsafe { close(self.child.stdin.as_ref().unwrap().as_raw_fd()); }
    }

    pub fn read_packets(&mut self) -> String {
        if self.protocols.contains(BIN) {
            let size = self.reader.read_u32::<LittleEndian>().unwrap();
            let mut packet = Vec::with_capacity(size as usize);
            self.reader.read(&mut packet).unwrap();

            String::from_utf8(packet).unwrap()
        } else {
            let mut line = String::new();
            self.reader.read_line(&mut line);
            line
        }
    }
}

