package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_10_4Test {

    @Test
    public void testgetRecordNumber_normalCase() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        HashMap<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 42L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        long result = invokeGetRecordNumber(csvRecord);

        // Assert
        Assertions.assertEquals(recordNumber, result);
    }

    @Test
    public void testgetRecordNumber_zeroRecordNumber() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        HashMap<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 0L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        long result = invokeGetRecordNumber(csvRecord);

        // Assert
        Assertions.assertEquals(recordNumber, result);
    }

    @Test
    public void testgetRecordNumber_negativeRecordNumber() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        HashMap<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = -1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        long result = invokeGetRecordNumber(csvRecord);

        // Assert
        Assertions.assertEquals(recordNumber, result);
    }

    private long invokeGetRecordNumber(CSVRecord csvRecord) throws Exception {
        Field field = CSVRecord.class.getDeclaredField("recordNumber");
        field.setAccessible(true);
        return (long) field.get(csvRecord);
    }
}