# Printable PKCS-7
## Web app to convert electronically signed documents to printable format.

To achieve the idea of making the signed document "readable", the application
follows the [ГОСТ Р 7.0.97-2016](https://www.consultant.ru/document/cons_doc_LAW_216461/) recommendation of information that should the stamp contain.
It follows:
1. Verification that document was signed electronically
2. Serial number of certificate
3. Owner's (signer's) common name
4. (Additionally) Document expiration date
5. (Additionally) Publisher's common name