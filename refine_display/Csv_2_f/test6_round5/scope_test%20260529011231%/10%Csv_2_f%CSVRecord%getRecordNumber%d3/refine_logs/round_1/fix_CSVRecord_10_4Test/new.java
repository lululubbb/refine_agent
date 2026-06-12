package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;

public class CSVRecord_10_4Test {

    @Test
    public void testGetRecordNumber_normalCase() throws Exception {
        long expectedRecordNumber = 10L;
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, record.getRecordNumber());
    }

    @Test
    public void testGetRecordNumber_zeroRecordNumber() throws Exception {
        long expectedRecordNumber = 0L;
        CSVRecord record = createCSVRecord(new String[]{"value1"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, record.getRecordNumber());
    }

    @Test
    public void testGetRecordNumber_negativeRecordNumber() throws Exception {
        long expectedRecordNumber = -5L;
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, record.getRecordNumber());
    }

    @Test
    public void testGetRecordNumber_largeRecordNumber() throws Exception {
        long expectedRecordNumber = Long.MAX_VALUE;
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, record.getRecordNumber());
    }

    @Test
    public void testGetRecordNumber_smallRecordNumber() throws Exception {
        long expectedRecordNumber = Long.MIN_VALUE;
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, record.getRecordNumber());
    }

    private CSVRecord createCSVRecord(String[] values, long recordNumber) throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, null, recordNumber);
    }
}