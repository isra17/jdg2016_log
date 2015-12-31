from util import error
import json
import select

class MissionManager:
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
        return Mission(mission, test)

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
        max_score = sum(m.score for m in self.all_missions)
        print("\n========== Results ==========")
        print("Nombre total de missions: {}".format(total))
        print("Missions non envoyées: {}".format(not_run))
        print("Missions sans réponse: {}".format(no_response))
        print("Mission répondue avec succès: {}/{}".format(passed, total))
        print("SCORE: {:.2f}/{:.2f} [{:.2f}%]".format(score, max_score, (score/max_score)*100))

class Mission:
    def __init__(self, mission, test):
        self.mission_id = mission['id']
        self.test_id = test['id']
        self.data = test['request']
        self.expected = test['expected']
        self.mission = mission
        self.score = test['score']
        self.result = False

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
        return self.score if self.result else 0


