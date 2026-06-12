package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_10_1Test {

    @Test
    public void testGetRecordNumber_normalCase() throws Exception {
        long expectedRecordNumber = 5L;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1", "value2"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, csvRecord.getRecordNumber());
    }

    @Test
    public void testGetRecordNumber_zeroRecordNumber() throws Exception {
        long expectedRecordNumber = 0L;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, csvRecord.getRecordNumber());
    }

    @Test
    public void testGetRecordNumber_negativeRecordNumber() throws Exception {
        long expectedRecordNumber = -1L;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1", "value2"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, csvRecord.getRecordNumber());
    }

    @Test
    public void testGetRecordNumber_boundaryValue() throws Exception {
        long expectedRecordNumber = Long.MAX_VALUE;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, csvRecord.getRecordNumber());
    }

    @Test
    public void testGetRecordNumber_exceptionCase() throws Exception {
        long expectedRecordNumber = Long.MIN_VALUE;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, csvRecord.getRecordNumber());
    }

    private CSVRecord createCSVRecord(String[] values, long recordNumber) throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, null, recordNumber);
    }
}