package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_10_3Test {
    private CSVRecord csvRecord;

    @BeforeEach
    public void setUp() {
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        String comment = "This is a comment";
        long recordNumber = 1L;

        csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
    }

    @Test
    public void testgetRecordNumber_normalCase() throws Exception {
        long expectedRecordNumber = 1L;
        long actualRecordNumber = csvRecord.getRecordNumber();
        assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testgetRecordNumber_edgeCase() throws Exception {
        CSVRecord edgeCaseRecord = new CSVRecord(new String[]{}, new HashMap<>(), null, 0L);
        long actualRecordNumber = edgeCaseRecord.getRecordNumber();
        assertEquals(0L, actualRecordNumber);
    }

    @Test
    public void testgetRecordNumber_negativeCase() throws Exception {
        CSVRecord negativeCaseRecord = new CSVRecord(new String[]{"value1"}, new HashMap<>(), "Negative case", -1L);
        long actualRecordNumber = negativeCaseRecord.getRecordNumber();
        assertEquals(-1L, actualRecordNumber);
    }

    @Test
    public void testgetRecordNumber_largeNumber() throws Exception {
        long largeRecordNumber = Long.MAX_VALUE;
        CSVRecord largeNumberRecord = new CSVRecord(new String[]{"value1"}, new HashMap<>(), "Large number case", largeRecordNumber);
        long actualRecordNumber = largeNumberRecord.getRecordNumber();
        assertEquals(largeRecordNumber, actualRecordNumber);
    }
    
    @Test
    public void testgetRecordNumber_zeroRecordNumber() throws Exception {
        CSVRecord zeroRecordNumberRecord = new CSVRecord(new String[]{"value1"}, new HashMap<>(), "Zero record number case", 0L);
        long actualRecordNumber = zeroRecordNumberRecord.getRecordNumber();
        assertEquals(0L, actualRecordNumber);
    }

    @Test
    public void testgetRecordNumber_minValue() throws Exception {
        CSVRecord minValueRecord = new CSVRecord(new String[]{"value1"}, new HashMap<>(), "Min value case", Long.MIN_VALUE);
        long actualRecordNumber = minValueRecord.getRecordNumber();
        assertEquals(Long.MIN_VALUE, actualRecordNumber);
    }

    @Test
    public void testgetRecordNumber_largeNegative() throws Exception {
        CSVRecord largeNegativeRecord = new CSVRecord(new String[]{"value1"}, new HashMap<>(), "Large negative case", Long.MIN_VALUE + 1);
        long actualRecordNumber = largeNegativeRecord.getRecordNumber();
        assertEquals(Long.MIN_VALUE + 1, actualRecordNumber);
    }

    @Test
    public void testgetRecordNumber_boundaryPositive() throws Exception {
        CSVRecord boundaryPositiveRecord = new CSVRecord(new String[]{"value1"}, new HashMap<>(), "Boundary positive case", 1L);
        long actualRecordNumber = boundaryPositiveRecord.getRecordNumber();
        assertEquals(1L, actualRecordNumber);
    }

    @Test
    public void testgetRecordNumber_nullValues() throws Exception {
        CSVRecord nullValuesRecord = new CSVRecord(null, new HashMap<>(), "Null values case", 1L);
        long actualRecordNumber = nullValuesRecord.getRecordNumber();
        assertEquals(1L, actualRecordNumber);
    }
}