from __future__ import annotations

import xml.etree.ElementTree as ET

from ..config import settings
from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, clean_text, unique, year_from_date


class PubMedClient(SourceClient):
    source_name = SourceName.pubmed
    request_delay_seconds = 0.34

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        term = request.query
        if request.start_year or request.end_year:
            start = request.start_year or 1800
            end = request.end_year or 3000
            term = f"({term}) AND ({start}:{end}[dp])"

        params = {
            "db": "pubmed",
            "term": term,
            "retmax": request.max_results_per_source,
            "retmode": "json",
            "tool": "phd_lit_metadata_engine",
        }
        if settings.contact_email:
            params["email"] = settings.contact_email
        if settings.ncbi_api_key:
            params["api_key"] = settings.ncbi_api_key

        search_data = await self.get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params)
        ids = search_data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        fetch_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
            "tool": "phd_lit_metadata_engine",
        }
        if settings.contact_email:
            fetch_params["email"] = settings.contact_email
        if settings.ncbi_api_key:
            fetch_params["api_key"] = settings.ncbi_api_key

        xml_text = await self.get_text("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params=fetch_params)
        root = ET.fromstring(xml_text)
        records: list[PaperRecord] = []

        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            article_node = medline.find("Article") if medline is not None else None
            if medline is None or article_node is None:
                continue

            pmid = clean_text(medline.findtext("PMID"))
            title = clean_text(article_node.findtext("ArticleTitle"))
            abstract_parts = [clean_text(node.text) for node in article_node.findall(".//Abstract/AbstractText")]
            authors = []
            for author in article_node.findall(".//AuthorList/Author"):
                collective = clean_text(author.findtext("CollectiveName"))
                if collective:
                    authors.append(collective)
                    continue
                last = clean_text(author.findtext("LastName"))
                fore = clean_text(author.findtext("ForeName"))
                full = " ".join(part for part in [fore, last] if part)
                if full:
                    authors.append(full)

            keywords = [clean_text(node.text) for node in medline.findall(".//KeywordList/Keyword")]
            pub_types = [clean_text(node.text) for node in article_node.findall(".//PublicationTypeList/PublicationType")]
            article_ids = {
                clean_text(node.attrib.get("IdType", "")): clean_text(node.text)
                for node in article.findall(".//PubmedData/ArticleIdList/ArticleId")
            }
            journal = clean_text(article_node.findtext(".//Journal/Title"))
            issn = clean_text(article_node.findtext(".//Journal/ISSN"))
            year = year_from_date(article_node.findtext(".//JournalIssue/PubDate/Year")) or year_from_date(
                article_node.findtext(".//ArticleDate/Year")
            )

            record = PaperRecord(
                title=title,
                abstract=" ".join(part for part in abstract_parts if part),
                author_keywords=unique(keywords),
                authors=unique(authors),
                year=year,
                doi=article_ids.get("doi", ""),
                pmid=pmid,
                pmcid=article_ids.get("pmc", ""),
                issn=issn,
                journal=journal,
                publication_type="; ".join(pub_types),
                source_databases=["pubmed"],
                source_urls=[f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"] if pmid else [],
                raw_ids={"pubmed": pmid},
            ).finalize_flags()
            records.append(record)

        return records
