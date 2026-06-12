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
}