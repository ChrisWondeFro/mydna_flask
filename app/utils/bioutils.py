from flask import Blueprint, request, jsonify
from Bio import SeqIO, Entrez, AlignIO, Phylo
from Bio.Seq import Seq
from Bio.Blast import NCBIWWW, NCBIXML

bioutils_bp = Blueprint('bioutils', __name__)

@bioutils_bp.route('/seq/complement', methods=['POST'])
def complement_sequence():
    sequence = Seq(request.json['sequence'])
    complement = sequence.complement()
    return jsonify(str(complement))

@bioutils_bp.route('/seq/read', methods=['POST'])
def read_seq_file():
    file_path = request.json['file_path']
    file_type = request.json['file_type']
    sequences = list(SeqIO.parse(file_path, file_type))
    return jsonify([str(seq.seq) for seq in sequences])

@bioutils_bp.route('/entrez/search', methods=['POST'])
def entrez_search():
    database = request.json['database']
    term = request.json['term']
    api_key = request.json.get('api_key', None)
    Entrez.api_key = api_key
    handle = Entrez.esearch(db=database, term=term)
    record = Entrez.read(handle)
    handle.close()
    return jsonify(record)

@bioutils_bp.route('/blast', methods=['POST'])
def blast_seq():
    sequence = request.json['sequence']
    database = request.json.get('database', 'nt')
    blast_program = request.json.get('blast_program', 'blastn')
    result_handle = NCBIWWW.qblast(blast_program, database, sequence)
    blast_record = NCBIXML.read(result_handle)
    alignments = [str(alignment.title) for alignment in blast_record.alignments]
    return jsonify(alignments)
