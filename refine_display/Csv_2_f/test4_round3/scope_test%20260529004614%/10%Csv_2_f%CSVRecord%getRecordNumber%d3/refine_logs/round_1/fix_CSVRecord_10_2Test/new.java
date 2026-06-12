package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

public class CSVRecord_10_2Test {

    @Test
    public void testGetRecordNumber_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Test comment";
        long recordNumber = 12345L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        long result = record.getRecordNumber();

        Assertions.assertEquals(12345L, result);
    }

    @Test
    public void testGetRecordNumber_zeroRecordNumber() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Test comment";
        long recordNumber = 0L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        long result = record.getRecordNumber();

        Assertions.assertEquals(0L, result);
    }

    @Test
    public void testGetRecordNumber_negativeRecordNumber() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Test comment";
        long recordNumber = -1L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        long result = record.getRecordNumber();

        Assertions.assertEquals(-1L, result);
    }
}