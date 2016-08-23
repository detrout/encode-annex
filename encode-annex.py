#!/usr/bin/env python3

import argparse
import logging
import netrc
import os
import subprocess
import sys
import requests

logger = logging.getLogger('encode-annex')


def main(cmdline=None):
    parser = make_parser()

    args = parser.parse_args(cmdline)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARN)

    if not verify_annex(args.destination, create=args.init):
        return 1

    auth = get_netrc(args.host)

    files_tracked = 0
    for object_id in args.experiments:
        obj = get_experiment(object_id, args.host, auth)
        with chdirContext(args.destination):
            files_tracked += annex_encode_files(obj, args.host, auth, args.fast)

    if files_tracked > 0:
        git_commit(args.destination, args.experiments)

    return 0


def make_parser():
    parser = argparse.ArgumentParser(
        '%prog: initialize a git-annex repository with an ENCODE Project experiment')
    parser.add_argument('experiments', nargs='*',
                        help='experiment IDs to download')
    parser.add_argument('-i', '--init', default=False, action='store_true',
                        help='initialize directory if needed')
    parser.add_argument('-d', '--destination', default=os.getcwd(),
                        help='directory do download things into',)
    parser.add_argument('--fast', action='store_true', default=False,
                        help="Don't automatically download files")
    parser.add_argument('--host', default='www.encodeproject.org',
                        help='what DCC host to to connect to')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='Increase logging (Report info messages)')
    parser.add_argument('-vv', '--debug', default=False, action='store_true',
                        help='report debug messages')
    return parser


def verify_annex(target, create=False):
    """Make sure target is a git annex directory
    """
    if not os.path.isdir(target):
        if create:
            os.mkdir(target)
        else:
            logger.error('%s is not a directory, please create it', target)
            return False

    git_dir = os.path.join(target, '.git')
    if not os.path.isdir(git_dir):
        if create:
            git_init(target)
        else:
            logger.error("%s is not a git directory. Please run git init %s", target, target)
            return False

    annex_dir = os.path.join(git_dir, 'annex')
    if not os.path.isdir(annex_dir):
        if create:
            annex_init(target)
        else:
            logger.error(
                '%s is not a git-annex directory please cd %s; git annex init',
                target,
                target)
            return False

    return True


def get_experiment(experiment, host, auth=None):
    """Request an ENCODE object from a url
    """
    base = 'https://{host}/experiments/{experiment}'
    url = base.format(host=host, experiment=experiment)
    obj = encoded_get(url, auth)
    if u'Experiment' not in obj.get('@type', []):
        raise ValueError("Returned object not an experiment")

    return obj


def encoded_get(url, auth=None):
    response = requests.get(url, auth=auth, params={'format': 'json'})
    if response.status_code != 200:
        raise requests.HTTPError(
            "Unable to open {} result {}".format(url, response.status_code))

    return response.json()

def annex_encode_files(experiment, host, auth, fast=False):
    """annex files from the experiment attaching some useful metadata.
    """
    files_tracked = 0
    useful = {
        'Experiment': set(['assay_term_name', 'assay_term_id',
                          'biosample_term_name', 'biosample_term_id', 'biosample_type',
                          'dbxrefs', 'target',
                          ]),
        'File': set(['aliases', 'accession', 'assembly',
                     'dataset', 'date_created',
                     'file_format', 'genome_annotation',
                     'output_category', 'output_type',
                     'status', 'submitted_file_name',
                     'uuid', 'replicate'
                      ]),
        'Replicate': set(['biological_replicate_number', 'technical_replicate_number',
                          'paired_ended', 'library']),
        'Library': set(['aliases', 'biosample', 'description',
                        'nucleic_acid_starting_quantity',
                        'nucleic_acid_starting_units',
        ]),
        'Biosample': set(['life_stage',
                          'model_organism_age',
                          'model_organism_age_units'])
    }
    experiment_metadata = generate_metadata(experiment, useful)
    for file_object in experiment['files']:
        url = 'https://' + host + file_object['href']
        _, name = os.path.split(file_object['href'])
        #name = file_object['accession'] + '.' + file_object['file_format']
        if not (os.path.islink(name) or os.path.exists(name)):
            annex_addurl(name, url, fast)
            files_tracked += 1

        metadata = experiment_metadata.copy()
        metadata.extend(generate_metadata(file_object, useful))

        annex_metadata(name, metadata)

    return files_tracked


def generate_metadata(encode_object, useful):
    """Generate metadata options from an encode object and interesting keys.
    """
    metadata = []

    types = [x for x in encode_object['@type'] if x in useful]
    object_type = types[0]
    for key in encode_object:
        if key in useful[object_type]:
            value = encode_object[key]
            # using 'label' as the target name would be silly, so we special case it
            if key == 'target':
                target = encode_object['target'].get('label')
                if target:
                    metadata.extend(['-s', 'target={}'.format(target)])
            elif key == 'dataset':
                _, dataset = os.path.split(value[:-1])
                metadata.extend(['-s', 'dataset={}'.format(dataset)])
            elif key == 'replicate':
                metadata.extend(generate_metadata(encode_object['replicate'], useful))
            elif key == 'library':
                metadata.extend(generate_metadata(encode_object['library'], useful))
            elif key == 'biosample':
                biosample_id = encode_object['biosample']['accession']
                metadata.extend(['-s', 'biosample={}'.format(biosample_id)])
                metadata.extend(generate_metadata(encode_object['biosample'], useful))
            elif key == 'lab':
                metadata.extend(generate_metadata(encode_object['lab'], useful))
            elif isinstance(value, list):
                for subvalue in value:
                    metadata.extend(['-s', '{}+={}'.format(key, subvalue)])
            else:
                metadata.extend(['-s', '{}={}'.format(key, value)])
    return metadata


def get_netrc(host):
    session = netrc.netrc()
    authenticators = session.authenticators(host)
    if authenticators:
        return (authenticators[0], authenticators[2])


def git_init(target):
    """Run git init to initialze a directory as a repository
    """
    run_command(['git', 'init', target])


def git_commit(target, experiments):
    """Run git-commit
    """
    with chdirContext(target):
        run_command(
            ['git', 'commit',
             '-m', 'Annexed encode objects: ' + ','.join(experiments)])


def annex_init(target):
    """Run git-annex init in a directory
    """
    with chdirContext(target):
        run_command(['git-annex', 'init'])


def annex_addurl(name, url, fast=False):
    """Annex url
    """
    command = ['git-annex', 'addurl']
    if logger.level >= logging.DEBUG:
        command.append('--debug')
    elif logger.level >= logging.INFO:
        command.append('--verbose')

    if fast:
        command.append('--fast')

    command.extend(['--file', name, url])
    run_command(command)


def annex_metadata(name, metadata):
    """Attach meta-data to a file.

    requires a metadata list already in a git-annex friendly format.
    e.g. -s name=value name+=value etc.
    """
    cmd = ['git-annex', 'metadata', name]
    cmd.extend(metadata)
    run_command(cmd)


def run_command(cmd):
    logger.debug(cmd)
    subprocess.check_call(cmd)

class chdirContext(object):
    def __init__(self, new_directory):
        self.cur_dir = None
        self.new_directory = new_directory

    def __enter__(self):
        self.cur_dir = os.getcwd()
        os.chdir(self.new_directory)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.cur_dir)
    
if __name__ == "__main__":
    sys.exit(main())
