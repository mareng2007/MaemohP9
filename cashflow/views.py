from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsCashflowUser  # ตรวจสิทธิ์ “cashflow_access”

from .models import (
    BankAccount,
    PostFinanceFacility,
    PNLoanUsage,
    ITDLoan,
    CashTransaction,
    ProjectCashAccount,
    CashFlowForecast,
    CommitteeMember,
    PaymentRequest,
    PaymentRequestItem,
    Vote,
    LCRequest,
    SwiftMessage,
    TRRequest,
    PNTicket,
    CashPayment
)
from .serializers import (
    BankAccountSerializer,
    PostFinanceFacilitySerializer,
    PNLoanUsageSerializer,
    ITDLoanSerializer,
    CashTransactionSerializer,
    ProjectCashAccountSerializer,
    CashFlowForecastSerializer,
    CommitteeMemberSerializer,
    PaymentRequestSerializer,
    PaymentRequestItemSerializer,
    VoteSerializer,
    LCRequestSerializer,
    SwiftMessageSerializer,
    TRRequestSerializer,
    PNTicketSerializer,
    CashPaymentSerializer
)

from decimal import Decimal
from datetime import date
from .tasks import run_cashflow_projection_task

PERMS = [IsAuthenticated, IsCashflowUser]


class BankAccountViewSet(viewsets.ModelViewSet):
    """
    จัดการ BankAccount (เพิ่ม / แก้ไข / ลบ)
    """
    queryset = BankAccount.objects.all().order_by('bank_name')
    serializer_class = BankAccountSerializer
    permission_classes = PERMS
    app_label = 'cashflow'


class PostFinanceFacilityViewSet(viewsets.ModelViewSet):
    """
    จัดการ PostFinanceFacility (วงเงิน PostFinance ที่ต้องขออนุมัติก่อนขอ PN)
    """
    queryset = PostFinanceFacility.objects.all().order_by('-start_date')
    serializer_class = PostFinanceFacilitySerializer
    permission_classes = PERMS
    app_label = 'cashflow'


class PNLoanUsageViewSet(viewsets.ModelViewSet):
    """
    จัดการสินเชื่อ PNAgainstPayment
    """
    queryset = PNLoanUsage.objects.all().order_by('-date')
    serializer_class = PNLoanUsageSerializer
    permission_classes = PERMS
    app_label = 'cashflow'


class ITDLoanViewSet(viewsets.ModelViewSet):
    """
    จัดการ ITDLoan (วงเงินสนับสนุน 300MB จาก HQ)
    """
    queryset = ITDLoan.objects.all().order_by('-created_on')
    serializer_class = ITDLoanSerializer
    permission_classes = PERMS
    app_label = 'cashflow'

    @action(detail=True, methods=['POST'])
    def use_funds(self, request, pk=None):
        """
        เมื่อใช้เงิน ITD → สร้าง CashTransaction 'ITDLoan_Usage'
        body: { "amount": ..., "description": "...", "bank_account": <id> }
        """
        loan = self.get_object()
        amount = Decimal(request.data.get('amount', '0'))
        description = request.data.get('description', '')
        bank_id = request.data.get('bank_account')
        if loan.used_amount + amount > loan.total_amount:
            return Response(
                {"detail": "วงเงิน ITDLoan ไม่เพียงพอ"},
                status=status.HTTP_400_BAD_REQUEST
            )
        bank_acc = BankAccount.objects.get(id=bank_id) if bank_id else None
        tx = CashTransaction.objects.create(
            transaction_date=date.today(),
            transaction_type='ITDLoan_Usage',
            related_id=loan.id,
            amount=amount,
            is_inflow=False,
            description=description,
            bank_account=bank_acc
        )
        loan.used_amount += amount
        loan.save(update_fields=['used_amount'])
        serializer = CashTransactionSerializer(tx)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CashTransactionViewSet(viewsets.ModelViewSet):
    """
    จัดการ CashTransaction (สร้าง / ดู / แก้ไข / ลบ)
    - ยอด BankAccount & ProjectCashAccount จะอัปเดตอัตโนมัติใน Serializer.create()
    """
    queryset = CashTransaction.objects.all().order_by('-transaction_date')
    serializer_class = CashTransactionSerializer
    permission_classes = PERMS
    app_label = 'cashflow'


class ProjectCashAccountViewSet(viewsets.ModelViewSet):
    """
    จัดการ ProjectCashAccount (Balance ประจำวัน)
    """
    queryset = ProjectCashAccount.objects.all().order_by('-date')
    serializer_class = ProjectCashAccountSerializer
    permission_classes = PERMS
    app_label = 'cashflow'


class CashFlowForecastViewSet(viewsets.ModelViewSet):
    """
    จัดการ CashFlowForecast (Base/Worst/Best)
    """
    queryset = CashFlowForecast.objects.all().order_by('-forecast_month')
    serializer_class = CashFlowForecastSerializer
    permission_classes = PERMS
    app_label = 'cashflow'

    @action(detail=False, methods=['POST'])
    def run_projection(self, request):
        """
        เรียก Celery Task เพื่อรัน Cash Flow Projection
        body: {
            "start_month": "YYYY-MM-DD",
            "num_months": 12,
            "scenario": "Base"|"Worst"|"Best",
            "assumptions": {...}
        }
        """
        start_month = request.data.get('start_month')
        num_months = int(request.data.get('num_months', 12))
        scenario = request.data.get('scenario', 'Base')
        assumptions = request.data.get('assumptions', {})
        run_cashflow_projection_task.delay(start_month, num_months, assumptions, scenario)
        return Response({"detail": "Projection started"}, status=status.HTTP_202_ACCEPTED)


class CommitteeMemberViewSet(viewsets.ModelViewSet):
    """
    จัดการ CommitteeMember (สมาชิกกรรมการโหวต)
    """
    queryset = CommitteeMember.objects.all().order_by('user__username')
    serializer_class = CommitteeMemberSerializer
    permission_classes = PERMS
    app_label = 'cashflow'


class PaymentRequestViewSet(viewsets.ModelViewSet):
    """
    จัดการ PaymentRequest Workflow:
    - สร้างคำขอ
    - โหวตรายการ
    - Recommend รายการ
    - CFO Review
    - PD Approve
    - Execute (สร้าง LCRequest, PNTicket, CashPayment, ITDLoan Usage, SupplierCredit Usage)
    """
    queryset = PaymentRequest.objects.all().order_by('-created_on')
    serializer_class = PaymentRequestSerializer
    permission_classes = PERMS
    app_label = 'cashflow'

    @action(detail=True, methods=['POST'])
    def vote(self, request, pk=None):
        """
        CommitteeMember โหวตรายการย่อย
        body: { "member_id": <committee_member_id>, "items": [<item_id>, ...] }
        """
        pr = self.get_object()
        member_id = request.data.get('member_id')
        item_ids = request.data.get('items', [])
        member = CommitteeMember.objects.get(id=member_id)
        votes_created = []
        for item_id in item_ids:
            item = PaymentRequestItem.objects.get(id=item_id, payment_request=pr)
            if not Vote.objects.filter(member=member, item=item).exists():
                Vote.objects.create(member=member, item=item)
                item.vote_count += 1
                item.save(update_fields=['vote_count'])
            votes_created.append(item.id)
        return Response({"voted_items": votes_created}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def recommend(self, request, pk=None):
        """
        ระบบแนะนำรายการจากจำนวนโหวตสูงสุด
        คืนค่า ID ของ PaymentRequestItem ที่แนะนำ
        """
        pr = self.get_object()
        items = pr.items.all().order_by('-vote_count', '-amount')
        count = items.count()
        top_n = max(1, count // 2)
        recommended = []
        for idx, item in enumerate(items):
            if idx < top_n:
                item.chosen = True
                item.save(update_fields=['chosen'])
                recommended.append(item.id)
        return Response({"recommended": recommended}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def cfo_review(self, request, pk=None):
        """
        CFO ตรวจสอบรายการ chosen=True
        body: { "approved": True/False }
        """
        pr = self.get_object()
        approved = request.data.get('approved', False)
        if not approved:
            pr.status = 'Rejected'
            pr.save(update_fields=['status'])
            return Response({"detail": "PaymentRequest ถูกปฏิเสธโดย CFO"}, status=status.HTTP_200_OK)
        pr.status = 'CFO_Review'
        pr.save(update_fields=['status'])
        return Response({"detail": "CFO อนุมัติ → รอ PD Approve"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def pd_approve(self, request, pk=None):
        """
        PD ตรวจสอบรายการ CFO อนุมัติ
        body: { "approved": True/False }
        """
        pr = self.get_object()
        approved = request.data.get('approved', False)
        if not approved:
            pr.status = 'Rejected'
            pr.save(update_fields=['status'])
            return Response({"detail": "PaymentRequest ถูกปฏิเสธโดย PD"}, status=status.HTTP_200_OK)
        pr.status = 'PD_Approval'
        pr.save(update_fields=['status'])
        return Response({"detail": "PD อนุมัติ → พร้อม Execute"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def execute(self, request, pk=None):
        """
        Execute การจ่ายเงิน:
        - LC → สร้าง LCRequest (status='Pending_ProfReview')
        - PN → สร้าง PNTicket (status='Pending')
        - Cash → สร้าง CashPayment (status='Pending')
        - ITDLoan → สร้าง CashTransaction 'ITDLoan_Usage'
        - SupplierCredit → สร้าง CashTransaction 'Supplier_Credit_Usage'
        """
        pr = self.get_object()
        if pr.status != 'PD_Approval':
            return Response(
                {"detail": "ไม่สามารถ Execute จนกว่าจะ PD Approve"},
                status=status.HTTP_400_BAD_REQUEST
            )

        executed_items = []
        for item in pr.items.filter(chosen=True):
            # —— กรณี LC ——
            if item.payment_type == 'LC':
                lc_req = LCRequest.objects.create(
                    payment_item=item,
                    bank_account=None,
                    lc_amount=item.amount,
                    status='Pending_ProfReview'
                )
                executed_items.append({'item_id': item.id, 'lc_request_id': lc_req.id})

            # —— กรณี PN ——
            elif item.payment_type == 'PN':
                pn_ticket = PNTicket.objects.create(
                    payment_item=item,
                    status='Pending'
                )
                executed_items.append({'item_id': item.id, 'pn_ticket_id': pn_ticket.id})

            # —— กรณี Cash ——
            elif item.payment_type == 'Cash':
                cash_pay = CashPayment.objects.create(
                    payment_item=item,
                    status='Pending'
                )
                executed_items.append({'item_id': item.id, 'cash_payment_id': cash_pay.id})

            # —— กรณี ITDLoan ——
            elif item.payment_type == 'ITDLoan':
                # สร้าง CashTransaction ใช้วงเงิน ITDLoan
                itdloan = ITDLoan.objects.first()  # สมมติมีวงเงินเดียว ถ้ามีหลาย เติม logic ดึงตาม ID
                if itdloan and itdloan.used_amount + item.amount <= itdloan.total_amount:
                    CashTransaction.objects.create(
                        transaction_date=date.today(),
                        transaction_type='ITDLoan_Usage',
                        related_id=itdloan.id,
                        amount=item.amount,
                        is_inflow=False,
                        description=f"Use ITDLoan for PaymentRequestItem {item.id}",
                        bank_account=None
                    )
                    itdloan.used_amount += item.amount
                    itdloan.save(update_fields=['used_amount'])
                    executed_items.append({'item_id': item.id, 'itdloan_usage': str(item.amount)})
                else:
                    # ถ้าวงเงิน ITD ไม่พอ → ไม่สร้าง และ return error รายการนี้
                    return Response(
                        {"detail": f"วงเงิน ITDLoan ไม่เพียงพอสำหรับ Item {item.id}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # —— กรณี SupplierCredit ——
            elif item.payment_type == 'SupplierCredit':
                supplier_credit = item.related_suppliercredit
                if supplier_credit and supplier_credit.remaining_credit() >= item.amount:
                    CashTransaction.objects.create(
                        transaction_date=date.today(),
                        transaction_type='Supplier_Credit_Usage',
                        related_id=supplier_credit.id,
                        amount=item.amount,
                        is_inflow=False,
                        description=f"Use SupplierCredit for PaymentRequestItem {item.id}",
                        bank_account=None
                    )
                    supplier_credit.used_amount += item.amount
                    supplier_credit.save(update_fields=['used_amount'])
                    executed_items.append({'item_id': item.id, 'supplier_credit_used': str(item.amount)})
                else:
                    return Response(
                        {"detail": f"วงเงินเครดิตจาก {supplier_credit.supplier_name} ไม่เพียงพอสำหรับ Item {item.id}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        pr.status = 'Executed'
        pr.save(update_fields=['status'])
        return Response({"executed": executed_items}, status=status.HTTP_200_OK)


class PaymentRequestItemViewSet(viewsets.ModelViewSet):
    """
    จัดการ PaymentRequestItem (สร้าง / ดู / แก้ไข / ลบ)
    """
    queryset = PaymentRequestItem.objects.all().order_by('-id')
    serializer_class = PaymentRequestItemSerializer
    permission_classes = PERMS
    app_label = 'cashflow'


class VoteViewSet(viewsets.ModelViewSet):
    """
    จัดการโหวต (Vote) ของ CommitteeMember
    """
    queryset = Vote.objects.all().order_by('-voted_on')
    serializer_class = VoteSerializer
    permission_classes = PERMS
    app_label = 'cashflow'


class LCRequestViewSet(viewsets.ModelViewSet):
    """
    จัดการ LCRequest Workflow
    """
    queryset = LCRequest.objects.all().order_by('-request_date')
    serializer_class = LCRequestSerializer
    permission_classes = PERMS
    app_label = 'cashflow'

    @action(detail=True, methods=['POST'])
    def professor_approve(self, request, pk=None):
        """
        อาจารย์ (Professor) อนุมัติ LCRequest
        """
        lc = self.get_object()
        if lc.status != 'Pending_ProfReview':
            return Response(
                {"detail": "ไม่สามารถอนุมัติก่อนอาจารย์ตรวจ"},
                status=status.HTTP_400_BAD_REQUEST
            )
        lc.status = 'Prof_Approved'
        lc.save(update_fields=['status'])
        return Response({"detail": "อาจารย์อนุมัติ LCRequest แล้ว"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def create_lc(self, request, pk=None):
        """
        สร้าง LC จริง (เมื่ออาจารย์อนุมัติแล้ว)
        body: { "lc_number": "...", "expiry_date": "YYYY-MM-DD", "bank_account": <id> }
        """
        lc = self.get_object()
        if lc.status != 'Prof_Approved':
            return Response(
                {"detail": "ไม่สามารถสร้าง LC ก่อนอาจารย์อนุมัติ"},
                status=status.HTTP_400_BAD_REQUEST
            )
        lc_number = request.data.get('lc_number')
        expiry_date = request.data.get('expiry_date')
        bank_id = request.data.get('bank_account')
        bank_acc = BankAccount.objects.get(id=bank_id) if bank_id else None

        lc.lc_number = lc_number
        lc.expiry_date = expiry_date
        lc.bank_account = bank_acc
        lc.status = 'LC_Created'
        lc.save(update_fields=['lc_number', 'expiry_date', 'status', 'bank_account'])
        return Response({"detail": "สร้าง LC เรียบร้อย"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def record_swift(self, request, pk=None):
        """
        บันทึก Swift Message จากธนาคาร (เมื่อ LC สร้างแล้ว)
        body: { "content": "..." }
        """
        lc = self.get_object()
        if lc.status != 'LC_Created':
            return Response(
                {"detail": "ไม่สามารถบันทึก Swift ก่อนสร้าง LC"},
                status=status.HTTP_400_BAD_REQUEST
            )
        content = request.data.get('content', '')
        swift = SwiftMessage.objects.create(lc_request=lc, content=content)
        lc.status = 'Swift_Sent'
        lc.save(update_fields=['status'])
        return Response({"swift_id": swift.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'])
    def rollback_to_tr(self, request, pk=None):
        """
        เมื่อครบ 180 วัน → แปลง LC เป็น TR (Manual Trigger)
        """
        lc = self.get_object()
        if lc.status != 'Swift_Sent':
            return Response(
                {"detail": "สถานะไม่ถูกต้องสำหรับการแปลงเป็น TR"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if date.today() < lc.expiry_date:
            return Response(
                {"detail": "ยังไม่ครบ 180 วัน"},
                status=status.HTTP_400_BAD_REQUEST
            )
        from .models import TRRequest
        tr = TRRequest.objects.create(
            lc_request=lc,
            tr_number=f"TR{lc.id}{date.today().strftime('%Y%m%d')}",
            tr_amount=lc.lc_amount,
            interest_rate=Decimal('5.00'),
            status='Active'
        )
        lc.status = 'TR_Converted'
        lc.save(update_fields=['status'])
        return Response({"tr_id": tr.id}, status=status.HTTP_201_CREATED)


class TRRequestViewSet(viewsets.ModelViewSet):
    """
    จัดการ TRRequest หลังแปลงจาก LC (Trust Receipt)
    """
    queryset = TRRequest.objects.all().order_by('-created_on')
    serializer_class = TRRequestSerializer
    permission_classes = PERMS
    app_label = 'cashflow'

    @action(detail=True, methods=['POST'])
    def repay(self, request, pk=None):
        """
        ชำระ TR
        body: { "amount": ..., "bank_account": <id> }
        """
        tr = self.get_object()
        amount = Decimal(request.data.get('amount', '0'))
        bank_id = request.data.get('bank_account')
        bank_acc = BankAccount.objects.get(id=bank_id) if bank_id else None

        tx = CashTransaction.objects.create(
            transaction_date=date.today(),
            transaction_type='TR_Payment',
            related_id=tr.id,
            amount=amount,
            is_inflow=False,
            description=f"Repay TR {tr.tr_number}",
            bank_account=bank_acc
        )
        tr.status = 'Repaid'
        tr.save(update_fields=['status'])
        return Response({"tx_id": tx.id}, status=status.HTTP_201_CREATED)


class PNTicketViewSet(viewsets.ModelViewSet):
    """
    จัดการ PNTicket (เมื่อ Execute PaymentRequestItem เป็น PN)
    """
    queryset = PNTicket.objects.all().order_by('-request_date')
    serializer_class = PNTicketSerializer
    permission_classes = PERMS
    app_label = 'cashflow'

    @action(detail=True, methods=['POST'])
    def approve(self, request, pk=None):
        """
        อาจารย์ตรวจเอกสาร PNTicket
        body: { "ticket_number": "...", "approved_on": optional (default=date.today()) }
        """
        ticket = self.get_object()
        if ticket.status != 'Pending':
            return Response(
                {"detail": "สถานะไม่ถูกต้อง"},
                status=status.HTTP_400_BAD_REQUEST
            )
        ticket.ticket_number = request.data.get('ticket_number', '')
        ticket.approved_on = date.today()
        ticket.status = 'Approved'
        ticket.save(update_fields=['ticket_number', 'approved_on', 'status'])
        return Response({"detail": "PNTicket อนุมัติแล้ว"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def execute(self, request, pk=None):
        """
        หลัง PNTicket approved → Issue PN (เบิกวงเงิน PN ที่เคยบันทึกไว้)
        body: { "bank_account": <id> }
        """
        ticket = self.get_object()
        if ticket.status != 'Approved':
            return Response(
                {"detail": "ยังไม่อนุมัติ"},
                status=status.HTTP_400_BAD_REQUEST
            )
        bank_id = request.data.get('bank_account')
        bank_acc = BankAccount.objects.get(id=bank_id) if bank_id else None
        amount = ticket.payment_item.amount

        # สร้าง CashTransaction (Outflow) PNTicket_Issue
        tx = CashTransaction.objects.create(
            transaction_date=date.today(),
            transaction_type='PNTicket_Issue',
            related_id=ticket.id,
            amount=amount,
            is_inflow=False,
            description=f"PNTicket Issue {ticket.ticket_number}",
            bank_account=bank_acc
        )
        ticket.status = 'Executed'
        ticket.save(update_fields=['status'])
        return Response({"tx_id": tx.id}, status=status.HTTP_201_CREATED)


class CashPaymentViewSet(viewsets.ModelViewSet):
    """
    จัดการ CashPayment (เช็คเงินสด)
    """
    queryset = CashPayment.objects.all().order_by('-request_date')
    serializer_class = CashPaymentSerializer
    permission_classes = PERMS
    app_label = 'cashflow'

    @action(detail=True, methods=['POST'])
    def issue_cheque(self, request, pk=None):
        """
        CFO/Accounting ออกเช็คจ่าย
        body: { "check_number": "...", "bank_account": <id> }
        """
        ch = self.get_object()
        if ch.status != 'Pending':
            return Response(
                {"detail": "สถานะไม่ถูกต้อง"},
                status=status.HTTP_400_BAD_REQUEST
            )
        ch.check_number = request.data.get('check_number', '')
        ch.issued_on = date.today()
        ch.status = 'Issued'
        ch.save(update_fields=['check_number', 'issued_on', 'status'])

        bank_id = request.data.get('bank_account')
        bank_acc = BankAccount.objects.get(id=bank_id) if bank_id else None

        tx = CashTransaction.objects.create(
            transaction_date=date.today(),
            transaction_type='Cash_Payment',
            related_id=ch.id,
            amount=ch.payment_item.amount,
            is_inflow=False,
            description=f"Cash payment for Item {ch.payment_item.id}",
            bank_account=bank_acc
        )
        return Response({"tx_id": tx.id}, status=status.HTTP_200_OK)



