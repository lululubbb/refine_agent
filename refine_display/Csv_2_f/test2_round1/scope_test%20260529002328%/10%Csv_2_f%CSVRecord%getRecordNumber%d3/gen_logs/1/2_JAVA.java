package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_10_1Test {

    @Test
    public void testGetRecordNumber_normalCase() throws Exception {
        long expectedRecordNumber = 5L;
        CSVRecord csvRecord = createCSVRecord(expectedRecordNumber);

        long actualRecordNumber = csvRecord.getRecordNumber();

        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGetRecordNumber_zeroRecordNumber() throws Exception {
        long expectedRecordNumber = 0L;
        CSVRecord csvRecord = createCSVRecord(expectedRecordNumber);

        long actualRecordNumber = csvRecord.getRecordNumber();

        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGetRecordNumber_negativeRecordNumber() throws Exception {
        long expectedRecordNumber = -1L;
        CSVRecord csvRecord = createCSVRecord(expectedRecordNumber);

        long actualRecordNumber = csvRecord.getRecordNumber();

        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    private CSVRecord createCSVRecord(long recordNumber) throws Exception {
        String[] values = new String[] {};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}