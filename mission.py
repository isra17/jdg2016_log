import time
import json
import select

class Mission:
    def __init__(self, mission, test):
        self.mission_id = mission['id']
        self.test_id = test['id']
        self.data = test['request']
        self.expected = test['expected']
        self.mission = mission
        self.test = test
        self.score = test['score']
        self.result = False

    def on_challenge(self):
        pass

    def validate(self, response):
        if response == self.expected:
            print('Challenge "{}" #{} passé'.format(self.mission['name'], self.test_id))
            self.result = True
        else:
            print('Challenge "{}" #{} échoué:\n' \
                  '\tRéponse attendue: {}\n' \
                  '\tRéponse reçue: {}'
                  .format(self.mission['name'], self.test_id, repr(self.expected),
                          repr(response)))

    def calc_score(self):
        return self.score * self.result

class Ping2Mission(Mission):
    def on_challenge(self):
        self.send_at = time.time()
        self.delay = int(self.test['request'])/1000

    def validate(self, response):
        if reponse == b'':
            print('Challenge "{}" #{} échoué:\n' \
                  '\tRéponse non-vide reçue: {}'
                  .format(self.mission['name'], self.test_id, repr(response)))
        elif time.time() < self.send_at + self.delay_ms:
            print('Challenge "{}" #{} échoué:\n' \
                    '\tRéponse reçue avant le délai demandé: {:.3f} s'
                  .format(self.mission['name'], self.test_id, time.time() - self.send_at))
        elif time.time() > self.send_at + self.delay + 0.5:
            print('Challenge "{}" #{} échoué:\n' \
                    '\tRéponse reçue après le délai demandé: {:.3f} s'
                  .format(self.mission['name'], self.test_id, time.time() - self.send_at))
        else:
            print('Challenge "{}" #{} passé'.format(self.mission['name'], self.test_id))
            self.result = True

class LabyrinthMission(Mission):
    def validate(self, response):
        if response == self.expected:
            print('Challenge "{}" #{} passé\n'\
                    .format(self.mission['name'], self.test_id))
            self.result = True
        try:
            directions = ' '.split(response)
            lab = self.test['request'].split(';')
            x,y = self.find_start(lab)
            for d in directions:
                x, y = self.move(lab, x, y, d)

            if lab[y][x] == 's':
                print('Challenge "{}" #{} partiellement passé\n'\
                        '\tChemin n\'est pas le plus court: {}'
                        .format(self.mission['name'], self.test_id, response))
                self.result = 0.6
            else:
                print('Challenge "{}" #{} échoué:\n' \
                        '\tChemin ne termine pas sur la sortie: {}'
                      .format(self.mission['name'], self.test_id, response))
        except Exception:
            print('Challenge "{}" #{} échoué:\n' \
                    '\tChemin invalide: {}'
                  .format(self.mission['name'], self.test_id, response))

    def move(self, lab, x, y, d):
        if d == 'U':
            y += 1
        elif d == 'R':
            x += 1
        elif d == 'D':
            y -= 1
        elif d == 'L':
            x -= 1
        else:
            raise ValueError()

        if self.is_valid(lab, x, y):
            return (x, y)
        else:
            raise ValueError()

    def is_valid(self, lab, x, y):
        if y < 0 or y >= len(lab) or x < 0 or x >= len(lab[y]):
            return False

        if lab[y][x] == '#':
            return False

    def find_start(self, lab):
        for y, l in enumerate(lab):
            if 'e' in l:
                return (l.index('e'), y)

class Labyrinth2Mission(LabyrinthMission):
    def validate(self, response):
        # Hack to reuse the parent class
        self.test['request'] = self.test['internal']
        super(LabyrinthMission, self).validate(response)
        if self.result == 0.6:
            self.result = (10/13)

    def move(self, lab, x, y, d):
        if d == 'UL':
            y += 1
        elif d == 'UR':
            x += 1
        elif d == 'DR':
            y -= 1
        elif d == 'DL':
            x -= 1
        else:
            raise ValueError()

        if self.is_valid(lab, x, y):
            return (x, y)
        else:
            raise ValueError()

class MissionManager:
    FactoryMap = {
        7: Ping2Mission,
        11: LabyrinthMission,
        12: Labyrinth2Mission,
    }

    def __init__(self, driver, include):
        self.include_ = include
        self.driver_ = driver
        self.test_id_ = 0
        self.to_run = []
        self.expected = {}
        self.results = []
        self.all_missions = []

    def load(self, file_path):
        self.data_ = json.load(open(file_path, 'r'))
        for data in self.data_['missions']:
            mission_id = data['id']
            if self.include_ and mission_id not in self.include_:
                continue
            for i, test in enumerate(data['tests']):
                test['score'] = data['score'] / len(data['tests'])
                test['id'] = i
                self.to_run.append(self.CreateMission(data, test))
        self.all_missions = self.to_run[:]

    def CreateMission(self, mission, test):
        mission_id = mission['id']
        factory = Mission
        if mission_id in self.FactoryMap:
            factory = self.FactoryMap[mission_id]
        return factory(mission, test)

    def run(self):
        writable = [self.driver_.popen_.stdin]
        while self.expected or self.to_run:
            rs, ws, es = select.select([self.driver_.popen_.stdout],
                                    writable,
                                    [], 5)
            for w in ws:
                self.send_challenge()

            for r in rs:
                self.read_response()

            if not self.to_run:
                writable = []

            if not (ws or rs):
                error("Temps de réponse trop lent (> 10 secondes)", self.driver_)

    def send_challenge(self):
        if not self.to_run:
            return
        challenge = self.to_run.pop(0)
        challenge.on_challenge()
        self.expected[self.test_id_] = challenge
        self.driver_.protocol_.send(self.test_id_, challenge.mission_id, challenge.data)
        self.test_id_ += 1

    def read_response(self):
        test_id, response = self.driver_.protocol_.recv()
        if test_id not in self.expected:
            error('ID de mission invalide: {}'.format(test_id), self)

        mission = self.expected[test_id]
        mission.validate(response)
        self.results.append(mission)
        del self.expected[test_id]

    def print_score(self):
        passed = sum(m.result for m in self.results)
        total = len(self.all_missions)
        responded = len(self.results)
        not_run = len(self.to_run)
        no_response = len(self.expected)
        score = sum(m.calc_score() for m in self.results)
        max_score = sum(m.score for m in self.all_missions) + 25
        protocol_score = self.protocol_score()
        score +=  protocol_score
        print("\n========== Results ==========")
        print("Nombre total de missions: {}".format(total))
        print("Missions non envoyées: {}".format(not_run))
        print("Missions sans réponse: {}".format(no_response))
        print("Mission répondue avec succès: {}/{}".format(passed, responded))
        print("Score de support du protocol: {}/{}".format(protocol_score, 25))
        print("SCORE: {:.2f}/{:.2f} [{:.2f}%]".format(score, max_score, (score/max_score)*100))

    def protocol_score(self):
        return sum([2 if b"T" in self.driver_.protocol_flags else 0,
                6 if b'B' in self.driver_.protocol_flags else 0,
                7 if b'R' in self.driver_.protocol_flags else 0,
                8 if b'C' in self.driver_.protocol_flags else 0,
                4 if b'S' in self.driver_.protocol_flags else 0])

