from sqlalchemy import create_engine, MetaData, Table, and_, select
from app.models import db
import numpy as np

class VariantDAO:
    def __init__(self, connection_string):
        self.connection_string = connection_string

    def get_variant_info(self, ids):
        engine = create_engine(self.connection_string)
        metadata = MetaData()
        variant_summary_table = Table('variant_summary_table', metadata, autoload_with=engine)

        batch_size = 5000
        id_chunks = np.array_split(ids, np.ceil(len(ids)/batch_size))

        rows = []
        for id_chunk in id_chunks:
            stmt = select(
                variant_summary_table.c.rs_dbsnp,
                variant_summary_table.c.assembly,
                variant_summary_table.c.clinicalsignificance,
                variant_summary_table.c.lastevaluated,
                variant_summary_table.c.reviewstatus,
                variant_summary_table.c.phenotypelist,
                variant_summary_table.c.phenotypeids,
            ).where(
                and_(
                    variant_summary_table.c.rs_dbsnp.in_(id_chunk.tolist()),
                    variant_summary_table.c.assembly == 'GRCh38'

                )
            )

            result = db.execute(stmt)
            rows.extend(result.fetchall())

        variant_infos = [row._asdict() for row in rows]

        return variant_infos
