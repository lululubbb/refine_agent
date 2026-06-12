package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_10_6Test {

    @Test
    public void testGetRecordNumber_normalCase() throws Exception {
        long expectedRecordNumber = 5L;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1", "value2"}, expectedRecordNumber);
        long actualRecordNumber = csvRecord.getRecordNumber();
        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGetRecordNumber_zeroRecordNumber() throws Exception {
        long expectedRecordNumber = 0L;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1"}, expectedRecordNumber);
        long actualRecordNumber = csvRecord.getRecordNumber();
        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGetRecordNumber_negativeRecordNumber() throws Exception {
        long expectedRecordNumber = -1L;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1", "value2", "value3"}, expectedRecordNumber);
        long actualRecordNumber = csvRecord.getRecordNumber();
        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGetRecordNumber_largeRecordNumber() throws Exception {
        long expectedRecordNumber = Long.MAX_VALUE;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1", "value2"}, expectedRecordNumber);
        long actualRecordNumber = csvRecord.getRecordNumber();
        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGetRecordNumber_smallestNegativeRecordNumber() throws Exception {
        long expectedRecordNumber = Long.MIN_VALUE;
        CSVRecord csvRecord = createCSVRecord(new String[]{"value1"}, expectedRecordNumber);
        long actualRecordNumber = csvRecord.getRecordNumber();
        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    private CSVRecord createCSVRecord(String[] values, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, new HashMap<>(), null, recordNumber);
    }
}