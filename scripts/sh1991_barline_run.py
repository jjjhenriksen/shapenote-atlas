#!/usr/bin/env python3
"""Run only the frozen five-image training experiment, with environment-aware caching."""
import argparse
import os
from pathlib import Path

import sh1991_pilot as pilot
import sh1991_fa_experiment as fa
from sh1991_fa_survival import verify_training_cohort


def immutable(path, value):
    if path.exists():
        if pilot.load(path) != value:
            raise ValueError('refusing changed configuration: ' + str(path))
    else:
        pilot.write(path, value)


def run(arm):
    work = pilot.DEFAULT_WORK / 'barline-v2'
    protocol = pilot.load(work / 'protocol.json')
    directory = work / arm
    dataset = pilot.load(fa.WORK / 'on' / 'dataset.json')
    verify_training_cohort(dataset, pilot.load(pilot.DEFAULT_WORK / 'dataset.json'), protocol['trainingProbe'])
    immutable(directory / 'dataset.json', dataset)
    toolchain = pilot.DEFAULT_WORK / 'toolchain'
    executable = toolchain / 'audiveris-barline-stemguard/app/build/install/app/bin/Audiveris'
    java_home = str((toolchain / 'jdk25/jdk-25.0.4.1+1/Contents/Home').resolve())
    java_opts = '-Datlas.barTrace=true -Datlas.faStemBarGuard=' + str(arm == 'revised').lower()
    constants = ['org.audiveris.omr.sheet.ProcessingSwitches.faHeads=true',
                 'org.audiveris.omr.Main.persistBatchCliConstants=false',
                 'org.audiveris.omr.sheet.note.NoteHeadsBuilder.dumpTemplateNotes=true']
    artifacts = [pilot.ROOT / 'experiments/audiveris-barline-v2' / name for name in
                 ('diagnostics.patch', 'fa-stem-guard.patch', 'FaStemBarGuardTest.java')]
    engine = {'engineIdentity': pilot.engine_identity(executable),
              'patches': {str(p.relative_to(pilot.ROOT)):pilot.digest(p.read_bytes()) for p in artifacts}}
    immutable(work / 'engine-stemguard.json', engine)
    # pilot.run's cache keys do not include JVM environment. Bind it here before
    # allowing either new recognition or cached receipts to be used.
    immutable(directory / 'execution.json', {'JAVA_HOME':java_home, 'JAVA_OPTS':java_opts,
               'engineIdentity':engine['engineIdentity'], 'constants':constants,
               'runnerSha256':pilot.digest(Path(__file__).read_bytes())})
    os.environ['JAVA_HOME'] = java_home
    os.environ['JAVA_OPTS'] = java_opts
    pilot.run(directory, executable, 2, 180, engine_constants=constants)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=('stemguard-off', 'revised'), required=True)
    run(parser.parse_args().arm)
