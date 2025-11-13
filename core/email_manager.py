import imaplib
import email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import Customer, Order, EmailLog, SessionLocal

class EmailManager:
    def __init__(self):
        self.imap_server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.email_account = os.getenv('EMAIL_ACCOUNT')
        self.email_password = os.getenv('EMAIL_PASSWORD')

        # Allow demo mode without credentials
        self.demo_mode = not self.email_account or not self.email_password

        # Allow test mode with dummy credentials
        self.test_mode = (
            self.email_account == 'test@example.com' and
            self.email_password == 'dummy_password_for_testing'
        )

        if self.demo_mode and not self.test_mode:
            print("📧 Demo mode: Email features disabled (no credentials configured)")
            print("   You can still use the API and web interface for testing")
        elif self.test_mode:
            print("📧 Test mode: Using dummy email credentials")

    def fetch_and_process_emails(self) -> List[Dict[str, Any]]:
        """Fetch new emails and return them for processing"""
        if self.demo_mode:
            print("📧 Demo mode: Returning existing email logs from database")
            # Return existing email logs from database for demo purposes
            return self._get_existing_email_logs()

        emails = self._fetch_new_emails()
        processed_emails = []

        for email_data in emails:
            try:
                # Log email in database
                logged_email = self._log_email(email_data, 'incoming')
                processed_emails.append({
                    'email_data': email_data,
                    'log_entry': logged_email
                })
            except Exception as e:
                print(f"Error processing email {email_data.get('id', 'unknown')}: {e}")

        return processed_emails

    def _get_existing_email_logs(self) -> List[Dict[str, Any]]:
        """Get existing email logs from database for demo mode"""
        db = SessionLocal()
        try:
            # Get recent email logs from database
            email_logs = db.query(EmailLog).order_by(EmailLog.received_at.desc()).limit(50).all()

            processed_emails = []
            for log in email_logs:
                email_data = {
                    'id': log.email_id,
                    'message_id': log.message_id or '',
                    'subject': log.subject or '',
                    'sender': log.sender or '',
                    'recipient': log.recipient or '',
                    'body': log.body or '',
                    'references': log.references or '',
                    'in_reply_to': log.in_reply_to or '',
                    'received_at': log.received_at,
                    'workflow_stage': log.workflow_stage,
                    'intent_summary': log.intent_summary,
                    'requires_action': log.requires_action
                }
                processed_emails.append({
                    'email_data': email_data,
                    'log_entry': log
                })

            print(f"📧 Demo mode: Returned {len(processed_emails)} existing email logs from database")
            return processed_emails

        except Exception as e:
            print(f"Error getting existing email logs: {e}")
            return []
        finally:
            db.close()

    def _fetch_new_emails(self) -> List[Dict[str, Any]]:
        """Fetch unread emails from inbox"""
        if self.demo_mode:
            print("📧 Demo mode: Skipping real email fetch")
            return []

        if self.test_mode:
            print("📧 Test mode: Skipping real email fetch")
            return []

        if not self.email_account or not self.email_password:
            print("📧 No email credentials: Skipping email fetch")
            return []

        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_account, self.email_password)
            mail.select('inbox')

            # Search for unread messages
            status, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()

            emails = []
            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)

                    # Extract email content
                    subject = self._get_header(email_message, 'subject') or ''
                    sender = self._get_header(email_message, 'from') or ''
                    message_id = self._get_header(email_message, 'Message-ID') or ''
                    references = self._get_header(email_message, 'References') or ''
                    in_reply_to = self._get_header(email_message, 'In-Reply-To') or ''

                    # Get email body
                    body = self._extract_email_body(email_message)

                    emails.append({
                        'id': email_id.decode(),
                        'message_id': message_id,
                        'subject': subject,
                        'sender': sender,
                        'body': body,
                        'references': references,
                        'in_reply_to': in_reply_to,
                        'raw_email': email_body,
                        'received_at': datetime.now()
                    })

                except Exception as e:
                    print(f"Error fetching email {email_id}: {e}")
                    continue

            mail.close()
            mail.logout()
            return emails

        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []

    def _get_header(self, email_message, header_name: str) -> str:
        """Safely get email header"""
        try:
            return email_message[header_name] or ''
        except:
            return ''

    def _extract_email_body(self, email_message) -> str:
        """Extract plain text body from email"""
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        break
                    except:
                        continue
        else:
            charset = email_message.get_content_charset() or 'utf-8'
            try:
                body = email_message.get_payload(decode=True).decode(charset, errors='ignore')
            except:
                body = str(email_message.get_payload())

        return body.strip()

    def _log_email(self, email_data: Dict, direction: str, order_id: int = None) -> EmailLog:
        """Log email in database"""
        db = SessionLocal()
        try:
            email_log = EmailLog(
                email_id=email_data['id'],
                direction=direction,
                subject=email_data['subject'],
                sender=email_data['sender'],
                recipient=self.email_account if direction == 'incoming' else email_data.get('recipient', ''),
                body=email_data['body'],
                message_id=email_data.get('message_id', ''),
                references=email_data.get('references', ''),
                in_reply_to=email_data.get('in_reply_to', ''),
                received_at=email_data['received_at'],
                order_id=order_id,
                workflow_stage=email_data.get('workflow_stage'),
                intent_summary=email_data.get('intent_summary'),
                requires_action=email_data.get('requires_action', True)
            )
            db.add(email_log)
            db.commit()
            db.refresh(email_log)
            return email_log
        except Exception as e:
            db.rollback()
            print(f"Error logging email: {e}")
            raise
        finally:
            db.close()

    def send_response_email(self, order_id: int, subject: str, body: str, attachments: List[str] = None, reply_to_message_id: str = None):
        """Send response email for an order with proper threading"""
        db = SessionLocal()
        try:
            # Get order and customer info
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise ValueError(f"Order {order_id} not found")

            customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
            if not customer:
                raise ValueError(f"Customer for order {order_id} not found")

            # Get threading information from the latest email in the chain
            threading_info = None
            if reply_to_message_id:
                # Find the email we're replying to
                reply_email = db.query(EmailLog).filter(EmailLog.message_id == reply_to_message_id).first()
                if reply_email:
                    threading_info = {
                        'in_reply_to': reply_email.message_id,
                        'references': reply_email.references or reply_email.message_id
                    }

            # Generate message ID for threading (even in test mode)
            message_id = f"<{uuid.uuid4()}@{self.email_account.split('@')[1]}>"

            # Send email with threading (skip in test mode)
            if not self.test_mode:
                message_id = self._send_email(customer.email, subject, body, attachments or [], threading_info)
                print(f"✅ Sent response email for order {order_id}")
            else:
                print(f"📧 Test mode: Simulating email send for order {order_id}")
                print(f"   Subject: {subject}")
                print(f"   Body preview: {body[:100]}...")

            # Determine workflow stage for outgoing email
            # If order is in 'follow_up' status, this is a follow-up response
            # Otherwise it's a regular response
            workflow_stage = 'FOLLOW_UP' if order.status == 'follow_up' else 'RESPONSE'

            # Log outgoing email with threading info (ALWAYS log, even in test mode)
            email_data = {
                'id': f"outbound_{order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'message_id': message_id,
                'subject': subject,
                'sender': self.email_account,
                'recipient': customer.email,
                'body': body,
                'in_reply_to': threading_info['in_reply_to'] if threading_info else '',
                'references': threading_info['references'] if threading_info else '',
                'received_at': datetime.now(),
                'workflow_stage': workflow_stage,
                'intent_summary': f'{"Follow-up" if workflow_stage == "FOLLOW_UP" else "Initial"} response sent to customer{" (TEST MODE)" if self.test_mode else ""}',
                'requires_action': False
            }
            print(f"📝 LOGGING OUTGOING EMAIL: {email_data['id']} for order {order_id}")
            logged_email = self._log_email(email_data, 'outgoing', order_id)
            print(f"✅ EMAIL LOGGED: ID {logged_email.id}, direction: {logged_email.direction}, workflow_stage: {logged_email.workflow_stage}")

        except Exception as e:
            print(f"Error sending response email for order {order_id}: {e}")
            raise
        finally:
            db.close()

    def _send_email(self, to_email: str, subject: str, body: str, attachments: List[str] = None, threading_info: Dict[str, str] = None) -> str:
        """Send email via SMTP with threading support"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_account
            msg['To'] = to_email
            msg['Subject'] = subject

            # Generate unique Message-ID for this email
            import uuid
            message_id = f"<{uuid.uuid4()}@{self.email_account.split('@')[1]}>"
            msg['Message-ID'] = message_id

            # Add threading headers if replying
            if threading_info:
                if threading_info.get('in_reply_to'):
                    msg['In-Reply-To'] = threading_info['in_reply_to']
                if threading_info.get('references'):
                    msg['References'] = threading_info['references']

            msg.attach(MIMEText(body, 'plain'))

            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            filename = os.path.basename(attachment_path)
                            part.add_header('Content-Disposition', f'attachment; filename={filename}')
                            msg.attach(part)

            server = smtplib.SMTP_SSL(self.smtp_server, 465)
            server.login(self.email_account, self.email_password)
            server.send_message(msg)
            server.quit()

            return message_id

        except Exception as e:
            print(f"Error sending email to {to_email}: {e}")
            raise

    def mark_email_as_read(self, email_id: str):
        """Mark email as read in IMAP"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_account, self.email_password)
            mail.select('inbox')
            mail.store(email_id, '+FLAGS', '\\Seen')
            mail.close()
            mail.logout()
        except Exception as e:
            print(f"Error marking email {email_id} as read: {e}")

    def get_customer_email_history(self, customer_email: str, limit: int = 10) -> List[Dict]:
        """Get email history for a customer"""
        db = SessionLocal()
        try:
            email_logs = db.query(EmailLog).filter(
                (EmailLog.sender == customer_email) | (EmailLog.recipient == customer_email)
            ).order_by(EmailLog.received_at.desc()).limit(limit).all()

            return [{
                'id': log.id,
                'direction': log.direction,
                'subject': log.subject,
                'received_at': log.received_at.isoformat(),
                'workflow_stage': log.workflow_stage,
                'intent_summary': log.intent_summary
            } for log in email_logs]

        finally:
            db.close()

    def extract_email_address(self, from_header: str) -> str:
        """Extract email address from From header"""
        import re
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1)
        return from_header.strip()

    def extract_name_from_email(self, from_header: str) -> str:
        """Extract name from From header"""
        import re
        match = re.search(r'([^<]+)', from_header)
        if match:
            return match.group(1).strip()
        return "Unknown Customer"

    def extract_email_from_content(self, content: str) -> str:
        """Extract email address from email content"""
        import re
        # Look for email patterns in the content
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, content)
        if matches:
            # Return the first email found (usually the contact email)
            return matches[0]
        return None
