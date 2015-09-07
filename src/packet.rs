use std::iter::repeat;

pub struct Packet {
    data : Vec<u8>
}

impl Packet {
    pub fn new(data : Vec<u8>) -> Packet {
        Packet{data: data}
    }

    fn deflate(&mut self) {
        if self.data.len() < 2 {
            return
        }

        let mut deflated = Vec::new();
        let mut p = 1usize;
        while p < self.data.len() {
            let c = self.data[p];
            if p + 2 <= self.data.len() && c == self.data[p+1] {
                let n = self.data[p+2];
                deflated.extend(repeat(c).take(n as usize));
                p += 2;
            } else {
                deflated.push(c);
                p += 1;
            }
        }

        self.data = deflated;
    }
}
